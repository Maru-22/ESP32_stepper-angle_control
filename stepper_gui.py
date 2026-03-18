import math
import time
import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports

BAUD = 115200
#Stepper_gui

def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


def normalize_360(angle_deg: float) -> float:
    return angle_deg % 360.0


class AngleDial(tk.Canvas):
    def __init__(self, master, size=420, **kwargs):
        super().__init__(
            master,
            width=size,
            height=size,
            bg="white",
            highlightthickness=1,
            **kwargs
        )
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self.r = size * 0.38

        self.display_angle = 0.0
        self.callback = None

        self.bind("<Button-1>", self.on_mouse)
        self.bind("<B1-Motion>", self.on_mouse)

        self.draw_dial()

    def set_callback(self, fn):
        self.callback = fn

    def set_angle(self, angle_deg: float):
        self.display_angle = normalize_360(angle_deg)
        self.draw_dial()

    def on_mouse(self, event):
        dx = event.x - self.cx
        dy = self.cy - event.y

        if dx == 0 and dy == 0:
            return

        ang = math.degrees(math.atan2(dy, dx))
        ang = normalize_360(ang)

        self.display_angle = ang
        self.draw_dial()

        if self.callback:
            self.callback(ang)

    def draw_dial(self):
        self.delete("all")

        # círculo principal
        self.create_oval(
            self.cx - self.r, self.cy - self.r,
            self.cx + self.r, self.cy + self.r,
            width=2
        )

        # ejes
        self.create_line(self.cx - self.r - 20, self.cy, self.cx + self.r + 20, self.cy, fill="gray")
        self.create_line(self.cx, self.cy - self.r - 20, self.cx, self.cy + self.r + 20, fill="gray")

        # marcas cada 10 grados, etiquetas cada 30
        for deg in range(0, 360, 10):
            rad = math.radians(deg)

            x1 = self.cx + (self.r - 8) * math.cos(rad)
            y1 = self.cy - (self.r - 8) * math.sin(rad)

            if deg % 30 == 0:
                x2 = self.cx + (self.r + 8) * math.cos(rad)
                y2 = self.cy - (self.r + 8) * math.sin(rad)
                self.create_line(x1, y1, x2, y2, width=2)

                tx = self.cx + (self.r + 28) * math.cos(rad)
                ty = self.cy - (self.r + 28) * math.sin(rad)
                self.create_text(tx, ty, text=str(deg), font=("Arial", 9))
            else:
                x2 = self.cx + (self.r + 4) * math.cos(rad)
                y2 = self.cy - (self.r + 4) * math.sin(rad)
                self.create_line(x1, y1, x2, y2)

        # flecha
        rad = math.radians(self.display_angle)
        x = self.cx + (self.r - 18) * math.cos(rad)
        y = self.cy - (self.r - 18) * math.sin(rad)

        self.create_line(self.cx, self.cy, x, y, width=3, arrow=tk.LAST, fill="red")

        # centro
        self.create_oval(self.cx - 4, self.cy - 4, self.cx + 4, self.cy + 4, fill="black")

        # texto inferior
        self.create_text(
            self.cx,
            self.cy + self.r + 45,
            text=f"Visual: {self.display_angle:.1f}°",
            font=("Arial", 11, "bold")
        )


class StepperGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control angular ESP32 Stepper")
        self.geometry("900x780")

        self.ser = None
        self.selected_angle = 0.0

        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        self.angle_var = tk.StringVar(value="0")
        self.steps_var = tk.StringVar(value="200")
        self.status_var = tk.StringVar(value="Desconectado")

        self.build_ui()

    def build_ui(self):
        # ===== barra superior =====
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Puerto:").pack(side="left")
        self.port_combo = ttk.Combobox(
            top,
            textvariable=self.port_var,
            values=list_ports(),
            width=22
        )
        self.port_combo.pack(side="left", padx=5)

        ttk.Button(top, text="Refrescar", command=self.refresh_ports).pack(side="left", padx=4)
        ttk.Button(top, text="Conectar", command=self.connect_serial).pack(side="left", padx=4)
        ttk.Button(top, text="Desconectar", command=self.disconnect_serial).pack(side="left", padx=4)

        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=15)

        # ===== dial =====
        dial_frame = ttk.LabelFrame(self, text="Selector angular", padding=10)
        dial_frame.pack(fill="x", padx=10, pady=10)

        self.dial = AngleDial(dial_frame, size=460)
        self.dial.pack()
        self.dial.set_callback(self.on_dial_changed)

        # ===== controles =====
        ctrl = ttk.LabelFrame(self, text="Control", padding=10)
        ctrl.pack(fill="x", padx=10, pady=10)

        row1 = ttk.Frame(ctrl)
        row1.pack(fill="x", pady=5)

        ttk.Label(row1, text="Ángulo manual (acepta negativos):").pack(side="left")
        self.angle_entry = ttk.Entry(row1, textvariable=self.angle_var, width=14)
        self.angle_entry.pack(side="left", padx=6)

        ttk.Button(row1, text="Actualizar círculo", command=self.update_dial_from_entry).pack(side="left", padx=4)
        ttk.Button(row1, text="Ir a ángulo", command=self.goto_angle).pack(side="left", padx=4)
        ttk.Button(row1, text="HOME", command=self.send_home).pack(side="left", padx=4)
        ttk.Button(row1, text="POS?", command=lambda: self.send_command("POS?")).pack(side="left", padx=4)

        row2 = ttk.Frame(ctrl)
        row2.pack(fill="x", pady=5)

        ttk.Button(row2, text="0°", command=lambda: self.quick_angle(0)).pack(side="left", padx=3)
        ttk.Button(row2, text="45°", command=lambda: self.quick_angle(45)).pack(side="left", padx=3)
        ttk.Button(row2, text="90°", command=lambda: self.quick_angle(90)).pack(side="left", padx=3)
        ttk.Button(row2, text="180°", command=lambda: self.quick_angle(180)).pack(side="left", padx=3)
        ttk.Button(row2, text="270°", command=lambda: self.quick_angle(270)).pack(side="left", padx=3)
        ttk.Button(row2, text="315°", command=lambda: self.quick_angle(315)).pack(side="left", padx=3)
        ttk.Button(row2, text="-45°", command=lambda: self.quick_angle(-45)).pack(side="left", padx=3)
        ttk.Button(row2, text="-90°", command=lambda: self.quick_angle(-90)).pack(side="left", padx=3)

        row3 = ttk.Frame(ctrl)
        row3.pack(fill="x", pady=8)

        ttk.Label(row3, text="Mover por pasos:").pack(side="left")
        ttk.Entry(row3, textvariable=self.steps_var, width=12).pack(side="left", padx=6)
        ttk.Button(row3, text="MOVE", command=self.move_steps).pack(side="left", padx=4)

        row4 = ttk.Frame(ctrl)
        row4.pack(fill="x", pady=5)

        self.visual_info = ttk.Label(
            row4,
            text="Ángulo lógico: 0.0° | Visual: 0.0°"
        )
        self.visual_info.pack(side="left")

        # ===== log =====
        logf = ttk.LabelFrame(self, text="Mensajes", padding=10)
        logf.pack(fill="both", expand=True, padx=10, pady=10)

        btns = ttk.Frame(logf)
        btns.pack(fill="x", pady=(0, 8))
        ttk.Button(btns, text="Clear log", command=self.clear_log).pack(side="left")

        self.log = tk.Text(logf, height=14, wrap="word")
        self.log.pack(fill="both", expand=True)

    def refresh_ports(self):
        self.port_combo["values"] = list_ports()
        self.log_message("Puertos actualizados.")

    def connect_serial(self):
        if self.ser and self.ser.is_open:
            self.log_message("Ya hay un puerto conectado.")
            return

        try:
            self.ser = serial.Serial(self.port_var.get(), BAUD, timeout=1)
            time.sleep(2)
            self.status_var.set(f"Conectado a {self.port_var.get()}")
            self.log_message(f"Conectado a {self.port_var.get()} @ {BAUD}")
            self.read_available()
        except Exception as e:
            messagebox.showerror("Error de conexión", str(e))

    def disconnect_serial(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.log_message("Puerto serial cerrado.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.status_var.set("Desconectado")

    def log_message(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def clear_log(self):
        self.log.delete("1.0", "end")

    def read_available(self):
        if not (self.ser and self.ser.is_open):
            return
        try:
            while self.ser.in_waiting:
                line = self.ser.readline().decode(errors="ignore").strip()
                if line:
                    self.log_message("ESP32: " + line)
        except Exception as e:
            self.log_message(f"Error leyendo serial: {e}")

    def send_command(self, cmd):
        if not (self.ser and self.ser.is_open):
            messagebox.showwarning("Sin conexión", "Primero conéctate al puerto serial.")
            return

        try:
            self.ser.write((cmd + "\n").encode())
            self.log_message("PC: " + cmd)
            time.sleep(0.08)
            self.read_available()
        except Exception as e:
            messagebox.showerror("Error enviando comando", str(e))

    def on_dial_changed(self, angle_0_360):
        self.selected_angle = angle_0_360
        self.angle_var.set(f"{angle_0_360:.1f}")
        self.update_info()

    def update_dial_from_entry(self):
        try:
            logical_angle = float(self.angle_var.get())
            self.selected_angle = logical_angle
            self.dial.set_angle(logical_angle)
            self.update_info()
        except ValueError:
            messagebox.showerror("Ángulo inválido", "Escribe un número válido.")

    def update_info(self):
        visual = normalize_360(self.selected_angle)
        self.visual_info.config(
            text=f"Ángulo lógico: {self.selected_angle:.1f}° | Visual: {visual:.1f}°"
        )

    def goto_angle(self):
        try:
            angle = float(self.angle_var.get())
            self.selected_angle = angle
            self.dial.set_angle(angle)
            self.update_info()
            self.send_command(f"GOTO {angle}")
        except ValueError:
            messagebox.showerror("Ángulo inválido", "Escribe un número válido.")

    def send_home(self):
        self.send_command("HOME")

    def move_steps(self):
        try:
            steps = int(self.steps_var.get())
            self.send_command(f"MOVE {steps}")
        except ValueError:
            messagebox.showerror("Pasos inválidos", "Escribe un entero válido.")

    def quick_angle(self, angle):
        self.angle_var.set(str(angle))
        self.goto_angle()


if __name__ == "__main__":
    app = StepperGUI()
    app.mainloop()
