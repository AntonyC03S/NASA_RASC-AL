from machine import Pin, PWM
from time import sleep

PWM_FREQ = 20000       # 20 kHz
MAX_DUTY = 65535

class DCMotor:
    def __init__(self, pin_a, pin_b, freq=PWM_FREQ):
        self.a = PWM(Pin(pin_a))
        self.b = PWM(Pin(pin_b))
        self.a.freq(freq)
        self.b.freq(freq)
        self.stop()

    def speed(self, value):
        """
        value: -100 to 100
        + = forward
        - = reverse
         0 = stop
        """
        value = max(-100, min(100, value))
        duty = int(abs(value) * MAX_DUTY / 100)

        if value > 0:
            self.a.duty_u16(duty)
            self.b.duty_u16(0)
        elif value < 0:
            self.a.duty_u16(0)
            self.b.duty_u16(duty)
        else:
            self.a.duty_u16(0)
            self.b.duty_u16(0)

    def stop(self):
        self.a.duty_u16(0)
        self.b.duty_u16(0)

    def deinit(self):
        self.a.deinit()
        self.b.deinit()


# Motor pin pairs for MOTION 2350 Pro
m1 = DCMotor(8, 9)      # M1A, M1B
m2 = DCMotor(10, 11)    # M2A, M2B
m3 = DCMotor(12, 13)    # M3A, M3B
m4 = DCMotor(14, 15)    # M4A, M4B

motors = [m1, m2, m3, m4]

def all_motors(speed):
    for m in motors:
        m.speed(speed)

try:
    while True:
        # all 4 motors forward at 60%
        all_motors(100)
        sleep(5)

        # stop
        all_motors(0)
        sleep(1)

        # all 4 motors reverse at 60%
        all_motors(-100)
        sleep(5)

        # stop
        all_motors(0)
        sleep(1)

        # each motor different speed
        m1.speed(30)
        m2.speed(50)
        m3.speed(70)
        m4.speed(100)
        sleep(2)

        all_motors(0)
        sleep(1)

except KeyboardInterrupt:
    all_motors(0)
    for m in motors:
        m.deinit()