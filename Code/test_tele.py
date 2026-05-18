import time
import board
import pwmio
import usb_cdc
from adafruit_motor import motor

# MOTION 2350 Pro M1 motor pins
M1A = pwmio.PWMOut(board.GP8, frequency=10000)
M1B = pwmio.PWMOut(board.GP9, frequency=10000)

motor1 = motor.DCMotor(M1A, M1B)

# Adjust these values
SPEED = 0.75          # 0.0 to 1.0
PULSE_TIME = 0.04    # seconds. Smaller = smaller movement

def stop():
    motor1.throttle = 0

def tiny_forward_step():
    motor1.throttle = SPEED
    time.sleep(PULSE_TIME)
    motor1.throttle = 0

def tiny_backward_step():
    motor1.throttle = -SPEED
    time.sleep(PULSE_TIME)
    motor1.throttle = 0

stop()

print("Ready.")
print("Send U = tiny forward step")
print("Send D = tiny backward step")
print("Send S = stop")

while True:
    if usb_cdc.console.in_waiting > 0:
        command = usb_cdc.console.read(1)

        if command == b"U":
            tiny_forward_step()
            print("Tiny forward step")

        elif command == b"D":
            tiny_backward_step()
            print("Tiny backward step")

        elif command == b"S":
            stop()
            print("Stop")

    time.sleep(0.005)