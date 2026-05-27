from machine import Pin, PWM, SoftI2C
import time
import sys
import uselect

# ============================================================
# Robot / lift controller
# ------------------------------------------------------------
# Hardware used:
#   - 4 DC motors driven through dual-PWM motor inputs
#   - 4 VL53L0X time-of-flight distance sensors on one I2C bus
#   - XSHUT pins used to assign unique I2C addresses to sensors
#
# Motor map:
#   M1 = Extension / retraction
#   M2 = Left vertical motor
#   M3 = Right vertical motor
#   M4 = Horizontal left / right motor
#
# Sensor map:
#   RH Vertical = right vertical height sensor
#   LH Vertical = left vertical height sensor
#   Horizontal  = horizontal distance sensor
#   Extender    = extension distance sensor
# ============================================================


# -----------------------------
# General configuration
# -----------------------------

PWM_FREQ = 20_000
DEFAULT_SPEED = 40_000
LEVEL_SPEED = 40_000
LEVEL_TOLERANCE_MM = 5

MAIN_MOVEMENT_TIME = 1.0
BACKUP_RUN_TIME = 3.0

SENSOR_OUTPUT_ENABLED = False
SENSOR_PRINT_INTERVAL = 0.25


# -----------------------------
# I2C / VL53L0X configuration
# -----------------------------

I2C_SDA = 3
I2C_SCL = 2

TOF_XSHUT_PINS = [18, 19, 27, 26]
TOF_SENSOR_NAMES = [
    "RH Vertical",
    "LH Vertical",
    "Horizontal",
    "Extender",
]
TOF_ADDRESSES = [0x30, 0x31, 0x32, 0x33]

try:
    import vl53l0x
    VL53L0X_AVAILABLE = True
except ImportError:
    VL53L0X_AVAILABLE = False

# One shared I2C bus for all time-of-flight sensors.
i2c = SoftI2C(
    sda=Pin(I2C_SDA),
    scl=Pin(I2C_SCL),
    freq=400_000,
)

# List of tuples: [(sensor_name, sensor_object), ...]
tof_sensors = []


# ============================================================
# TOF SENSOR HELPERS
# ============================================================

def setup_tof_sensors():
    """Initialize all VL53L0X sensors and assign unique I2C addresses.

    VL53L0X sensors all boot at the same default address. To run multiple
    sensors on the same bus, all sensors are first held in reset using XSHUT.
    Then each sensor is enabled one at a time and moved to a unique address.
    """
    global tof_sensors
    tof_sensors = []

    if not VL53L0X_AVAILABLE:
        print("VL53L0X library not found.")
        return

    print("Initializing VL53L0X sensors...")

    xshuts = [Pin(pin, Pin.OUT) for pin in TOF_XSHUT_PINS]

    # Hold every sensor in reset so only one sensor appears on the bus at a time.
    for xshut in xshuts:
        xshut.value(0)

    time.sleep(0.2)

    # Bring up each sensor individually and assign its new address.
    for index, xshut in enumerate(xshuts):
        sensor_name = TOF_SENSOR_NAMES[index]
        sensor_address = TOF_ADDRESSES[index]

        xshut.value(1)
        time.sleep(0.2)

        try:
            sensor = vl53l0x.VL53L0X(i2c)
            sensor.set_address(sensor_address)
            time.sleep(0.1)

            tof_sensors.append((sensor_name, sensor))
            print(sensor_name, "initialized at", hex(sensor_address))

        except Exception as error:
            print("Failed to initialize", sensor_name)
            print(error)

    print("VL53L0X setup complete.")
    print("I2C scan =", i2c.scan())
    print()


def get_distance(sensor):
    """Return one distance reading in millimeters."""
    return sensor.read_range_single_millimeters()


def get_sensor_by_name(target_name):
    """Return a sensor object by its configured name, or None if not found."""
    for name, sensor in tof_sensors:
        if name == target_name:
            return sensor
    return None


def get_vertical_distances():
    """Return RH and LH vertical sensor readings as (rh_mm, lh_mm).

    If either sensor is missing or a read fails, returns (None, None).
    """
    rh_sensor = get_sensor_by_name("RH Vertical")
    lh_sensor = get_sensor_by_name("LH Vertical")

    if rh_sensor is None or lh_sensor is None:
        return None, None

    try:
        rh = get_distance(rh_sensor)
        lh = get_distance(lh_sensor)
        return rh, lh
    except Exception:
        return None, None


def read_tof_sensors():
    """Return formatted distance strings for all initialized sensors."""
    readings = []

    for name, sensor in tof_sensors:
        try:
            distance = get_distance(sensor)
            readings.append("{}: {} mm".format(name, distance))
        except Exception as error:
            readings.append("{}: ERR {}".format(name, error))

    return readings


def print_sensor_distances():
    """Print one line containing all sensor distances."""
    print(" | ".join(read_tof_sensors()))


# ============================================================
# MOTOR SETUP
# ============================================================

# Each motor has two PWM inputs. Driving A while B is 0 moves one direction;
# driving B while A is 0 moves the opposite direction.
M1A = PWM(Pin(9))
M1B = PWM(Pin(8))

M2A = PWM(Pin(11))
M2B = PWM(Pin(10))

M3A = PWM(Pin(12))
M3B = PWM(Pin(13))

M4A = PWM(Pin(14))
M4B = PWM(Pin(15))

motors = [
    ("M1 Extension", M1A, M1B),
    ("M2 Vertical", M2A, M2B),
    ("M3 Vertical", M3A, M3B),
    ("M4 Horizontal", M4A, M4B),
]

for _, pin_a, pin_b in motors:
    pin_a.freq(PWM_FREQ)
    pin_b.freq(PWM_FREQ)


# ============================================================
# BASIC MOTOR HELPERS
# ============================================================

def motor_forward(pin_a, pin_b, speed=DEFAULT_SPEED):
    """Run a motor in its forward direction."""
    pin_a.duty_u16(speed)
    pin_b.duty_u16(0)


def motor_reverse(pin_a, pin_b, speed=DEFAULT_SPEED):
    """Run a motor in its reverse direction."""
    pin_a.duty_u16(0)
    pin_b.duty_u16(speed)


def motor_stop(pin_a, pin_b):
    """Stop one motor by setting both PWM inputs to 0."""
    pin_a.duty_u16(0)
    pin_b.duty_u16(0)


def stop_all():
    """Stop every motor immediately."""
    for _, pin_a, pin_b in motors:
        motor_stop(pin_a, pin_b)


# ============================================================
# NAMED MOTOR ACTIONS
# ============================================================

# M1: extension motor.
def extend_m1():
    motor_reverse(M1A, M1B)


def retract_m1():
    motor_forward(M1A, M1B)


def stop_m1():
    motor_stop(M1A, M1B)


# M2: left vertical motor.
def motor_2_down():
    motor_reverse(M2A, M2B)


def motor_2_up():
    motor_forward(M2A, M2B)


def stop_m2():
    motor_stop(M2A, M2B)


# M3: right vertical motor.
def motor_3_down():
    motor_reverse(M3A, M3B)


def motor_3_up():
    motor_forward(M3A, M3B)


def stop_m3():
    motor_stop(M3A, M3B)


def motors_2_and_3_stop():
    stop_m2()
    stop_m3()


# M4: horizontal motor.
def left_m4():
    motor_reverse(M4A, M4B)


def right_m4():
    motor_forward(M4A, M4B)


def stop_m4():
    motor_stop(M4A, M4B)


# ============================================================
# M2 / M3 AUTO-LEVEL HELPERS
# ============================================================

def move_m2(direction):
    """Move M2 up or down using the configured leveling speed."""
    if direction == "UP":
        motor_forward(M2A, M2B, LEVEL_SPEED)
    else:
        motor_reverse(M2A, M2B, LEVEL_SPEED)


def move_m3(direction):
    """Move M3 up or down using the configured leveling speed."""
    if direction == "UP":
        motor_forward(M3A, M3B, LEVEL_SPEED)
    else:
        motor_reverse(M3A, M3B, LEVEL_SPEED)


def auto_level_vertical(direction):
    """Move M2/M3 while trying to keep the left and right sides level.

    Original behavior preserved:
      - M2 is treated as the LH side.
      - M3 is treated as the RH side.
      - A larger vertical sensor distance is treated as the higher side.

    Verify this logic on the physical mechanism. Depending on sensor mounting
    and motor polarity, the correction direction may need to be inverted.
    """
    rh, lh = get_vertical_distances()

    # If sensors are unavailable, fall back to moving both motors together.
    if rh is None or lh is None:
        move_m2(direction)
        move_m3(direction)
        return

    # M2 = LH side, M3 = RH side.
    if lh > rh + LEVEL_TOLERANCE_MM:
        # LH side is higher than RH side.
        stop_m2()
        move_m3(direction)

    elif rh > lh + LEVEL_TOLERANCE_MM:
        # RH side is higher than LH side.
        move_m2(direction)
        stop_m3()

    else:
        # Close enough: move both sides together.
        move_m2(direction)
        move_m3(direction)


# ============================================================
# INPUT / LIVE CONTROL HELPERS
# ============================================================

def user_typed_stop(poll, typed):
    """Read stdin and return (should_stop, updated_typed_buffer)."""
    if not poll.poll(0):
        return False, typed

    ch = sys.stdin.read(1)

    if ch == "\n" or ch == "\r":
        if typed.strip().upper() == "S":
            return True, ""
        return False, ""

    return False, typed + ch


def maybe_print_live_sensors(last_sensor_print):
    """Print live sensor output if enabled and interval has elapsed.

    Returns the updated last print timestamp.
    """
    if not SENSOR_OUTPUT_ENABLED:
        return last_sensor_print

    now = time.ticks_ms()
    interval_ms = int(SENSOR_PRINT_INTERVAL * 1000)

    if time.ticks_diff(now, last_sensor_print) >= interval_ms:
        print_sensor_distances()
        return now

    return last_sensor_print


def live_manual_motion(action, label):
    """Start a manual motor action.

    If live sensor output is disabled, this preserves the original behavior:
    the action starts and the function returns immediately. The motor keeps
    running until another command stops it.

    If live sensor output is enabled, this enters a live loop and waits for
    the user to type S then Enter.
    """
    action()
    print(label)

    if not SENSOR_OUTPUT_ENABLED:
        return

    print("Live sensor output active.")
    print("Type S then Enter to stop.")

    poll = uselect.poll()
    poll.register(sys.stdin, uselect.POLLIN)

    typed = ""
    last_sensor_print = time.ticks_ms()

    while True:
        last_sensor_print = maybe_print_live_sensors(last_sensor_print)

        should_stop, typed = user_typed_stop(poll, typed)
        if should_stop:
            stop_all()
            print("Stopped all motors")
            break

        time.sleep(0.02)


def live_autolevel_motion(direction, label):
    """Run M2/M3 with auto-level correction until the user stops it."""
    print(label)
    print("Auto-level active. Keeping within", LEVEL_TOLERANCE_MM, "mm.")
    print("Type S then Enter to stop.")

    poll = uselect.poll()
    poll.register(sys.stdin, uselect.POLLIN)

    typed = ""
    last_sensor_print = time.ticks_ms()

    while True:
        auto_level_vertical(direction)
        last_sensor_print = maybe_print_live_sensors(last_sensor_print)

        should_stop, typed = user_typed_stop(poll, typed)
        if should_stop:
            stop_all()
            print("Stopped all motors")
            break

        time.sleep(0.02)


# ============================================================
# TIMED MOVEMENT HELPERS
# ============================================================

def run_for_time(action, stop_action, duration):
    """Run an action for a fixed number of seconds, then stop it."""
    start = time.ticks_ms()
    last_sensor_print = time.ticks_ms()

    action()

    while time.ticks_diff(time.ticks_ms(), start) < int(duration * 1000):
        last_sensor_print = maybe_print_live_sensors(last_sensor_print)
        time.sleep(0.02)

    stop_action()


def run_autolevel_for_time(direction, duration):
    """Run vertical auto-level movement for a fixed number of seconds."""
    start = time.ticks_ms()
    last_sensor_print = time.ticks_ms()

    while time.ticks_diff(time.ticks_ms(), start) < int(duration * 1000):
        auto_level_vertical(direction)
        last_sensor_print = maybe_print_live_sensors(last_sensor_print)
        time.sleep(0.02)

    motors_2_and_3_stop()


# ============================================================
# MENU PRINTING
# ============================================================

def print_main_help():
    print()
    print("Main UI")
    print("----------------")
    print("E = M1 Extend")
    print("O = M1 Retract")
    print("L = M4 Left")
    print("R = M4 Right")
    print("D = M2/M3 DOWN auto-level")
    print("U = M2/M3 UP auto-level")
    print("M = Manual UI")
    print("K = Back Up UI")
    print("S = Stop")
    print("H = Help")
    print("Q = Quit")
    print()


def print_manual_help():
    print()
    print("Manual Control UI")
    print("----------------")
    print("E  = M1 Extend")
    print("O  = M1 Retract")
    print("L  = M4 Left")
    print("R  = M4 Right")
    print("D  = M2/M3 DOWN auto-level")
    print("U  = M2/M3 UP auto-level")
    print("D2 = Motor 2 DOWN")
    print("U2 = Motor 2 UP")
    print("D3 = Motor 3 DOWN")
    print("U3 = Motor 3 UP")
    print("P  = Print distances")
    print("V  = Toggle live output")
    print("X  = Sensor debug")
    print("M  = Redisplay menu")
    print("S  = Stop all")
    print("B  = Back")
    print()


def print_backup_help():
    print()
    print("Back Up UI")
    print("----------------")
    print("Commands:")
    print("L = Left for 3 seconds")
    print("R = Right for 3 seconds")
    print("U = Up for 3 seconds")
    print("D = Down for 3 seconds")
    print("E = Extend for 3 seconds")
    print("O = Retract for 3 seconds")
    print("B = Return to main")
    print()


# ============================================================
# MENU HANDLERS
# ============================================================

def manual_menu():
    """Interactive manual-control menu."""
    global SENSOR_OUTPUT_ENABLED

    print_manual_help()

    while True:
        cmd = input("Manual Command: ").strip().upper()

        if cmd == "B":
            stop_all()
            print_main_help()
            break

        elif cmd == "M":
            print_manual_help()

        elif cmd == "S":
            stop_all()
            print("Stopped all motors")

        elif cmd == "P":
            print_sensor_distances()

        elif cmd == "V":
            SENSOR_OUTPUT_ENABLED = not SENSOR_OUTPUT_ENABLED
            if SENSOR_OUTPUT_ENABLED:
                print("Live distance output ENABLED.")
            else:
                print("Live distance output DISABLED.")

        elif cmd == "E":
            live_manual_motion(extend_m1, "M1 EXTEND")

        elif cmd == "O":
            live_manual_motion(retract_m1, "M1 RETRACT")

        elif cmd == "L":
            live_manual_motion(left_m4, "M4 LEFT")

        elif cmd == "R":
            live_manual_motion(right_m4, "M4 RIGHT")

        elif cmd == "D":
            live_autolevel_motion("DOWN", "M2/M3 DOWN AUTOLEVEL")

        elif cmd == "U":
            live_autolevel_motion("UP", "M2/M3 UP AUTOLEVEL")

        elif cmd == "D2":
            live_manual_motion(motor_2_down, "M2 DOWN")

        elif cmd == "U2":
            live_manual_motion(motor_2_up, "M2 UP")

        elif cmd == "D3":
            live_manual_motion(motor_3_down, "M3 DOWN")

        elif cmd == "U3":
            live_manual_motion(motor_3_up, "M3 UP")

        elif cmd == "X":
            print("VL53L0X_AVAILABLE =", VL53L0X_AVAILABLE)
            print("Sensors initialized =", len(tof_sensors))
            print("I2C scan =", i2c.scan())

        else:
            print("Invalid command")


def backup_menu():
    """Timed backup menu.

    These commands run for BACKUP_RUN_TIME seconds and then stop automatically.
    """
    print_backup_help()

    while True:
        cmd = input("Back Up Command: ").strip().upper()

        if cmd == "B":
            stop_all()
            print_main_help()
            break

        elif cmd == "L":
            run_for_time(left_m4, stop_m4, BACKUP_RUN_TIME)
            print("Backup LEFT complete")

        elif cmd == "R":
            run_for_time(right_m4, stop_m4, BACKUP_RUN_TIME)
            print("Backup RIGHT complete")

        elif cmd == "U":
            run_for_time(
                lambda: (motor_2_up(), motor_3_up()),
                motors_2_and_3_stop,
                BACKUP_RUN_TIME,
            )
            print("Backup UP complete")

        elif cmd == "D":
            run_for_time(
                lambda: (motor_2_down(), motor_3_down()),
                motors_2_and_3_stop,
                BACKUP_RUN_TIME,
            )
            print("Backup DOWN complete")

        elif cmd == "E":
            run_for_time(extend_m1, stop_m1, BACKUP_RUN_TIME)
            print("Backup EXTEND complete")

        elif cmd == "O":
            run_for_time(retract_m1, stop_m1, BACKUP_RUN_TIME)
            print("Backup RETRACT complete")

        else:
            print("Invalid command")


def main_menu():
    """Main command loop."""
    print_main_help()

    while True:
        cmd = input("Main Command: ").strip().upper()

        if cmd == "Q":
            stop_all()
            print("Exiting...")
            break

        elif cmd == "H":
            print_main_help()

        elif cmd == "S":
            stop_all()
            print("Stopped all motors")

        elif cmd == "M":
            manual_menu()

        elif cmd == "K":
            backup_menu()

        elif cmd == "E":
            run_for_time(extend_m1, stop_m1, MAIN_MOVEMENT_TIME)
            print("M1 EXTEND complete")

        elif cmd == "O":
            run_for_time(retract_m1, stop_m1, MAIN_MOVEMENT_TIME)
            print("M1 RETRACT complete")

        elif cmd == "L":
            run_for_time(left_m4, stop_m4, MAIN_MOVEMENT_TIME)
            print("M4 LEFT complete")

        elif cmd == "R":
            run_for_time(right_m4, stop_m4, MAIN_MOVEMENT_TIME)
            print("M4 RIGHT complete")

        elif cmd == "D":
            run_autolevel_for_time("DOWN", MAIN_MOVEMENT_TIME)
            print("M2/M3 DOWN complete")

        elif cmd == "U":
            run_autolevel_for_time("UP", MAIN_MOVEMENT_TIME)
            print("M2/M3 UP complete")

        else:
            print("Invalid command")


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

def main():
    """Initialize hardware and start the UI."""
    stop_all()
    setup_tof_sensors()
    main_menu()

if __name__ == "__main__":
    main()
