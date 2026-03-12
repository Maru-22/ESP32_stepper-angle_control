# ESP32_stepper-angle_control
Control por ángulos de un motor a pasos usando es32

# ESP32 Stepper Angle Control

Proyecto para controlar un motor NEMA17 con un ESP32 y un driver DRV8825/A4988.

## Requisitos

- ESP32 DOIT DEVKIT V1
- Driver DRV8825 o compatible
- Motor paso a paso 1.8°/step
- Fuente de 12V para el motor
- VS Code + PlatformIO
- Python 3 + pyserial

## Pines usados

- DIR -> GPIO 27
- STEP -> GPIO 26

## Conexiones importantes

- RST y SLP unidos a 3.3V
- EN a GND
- VMOT a 12V
- GND común entre ESP32, driver y fuente

## Comandos seriales

- HOME
- GOTO 90
- MOVE 200
- POS?
