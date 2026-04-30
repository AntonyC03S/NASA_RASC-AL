from machine import Pin, PWM
from time import sleep

# Change 0 to your servo signal GPIO if needed
SERVO_PIN = 0

servo = PWM(Pin(SERVO_PIN))
servo.freq(50)  # standard servo refresh rate: 50 Hz

def set_servo_us(us):
    # us = pulse width in microseconds
    servo.duty_ns(us * 1000)

def set_angle(angle):
    # Simple SG90-style mapping.
    # 0 deg  -> 500 us
    # 180 deg -> 2500 us
    angle = max(0, min(180, angle))
    us = int(500 + (2000 * angle / 180))
    set_servo_us(us)

while True:
    set_angle(0)
    sleep(1)

    set_angle(90)
    sleep(1)

    set_angle(180)
    sleep(1)