import serial
import time

PORT = "/dev/ttyACM1"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

time.sleep(2)

print("Conectado al ESP32.")
print("Escribe comandos: HOME, GOTO 90, MOVE 200, POS?")
print("Escribe 'exit' para salir.")

while True:
    cmd = input("> ")

    if cmd == "exit":
        break

    ser.write((cmd + "\n").encode())

    time.sleep(0.1)

    while ser.in_waiting:
        print("ESP32:", ser.readline().decode().strip())

ser.close()
