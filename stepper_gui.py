import math
import time
import tkinter as tk
from tkinter import ttk, messagebox

import serial
import serial.tools.list_ports

BAUD = 115200


def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


def normalize_360(angle_deg: float) -> float:
    return angle_deg % 360.0


class AngleDial(tk.Canvas):
    def __init__(self, master, size=420, **kwargs):
        super().__init__(master, width=size, height=size, bg="white", highlightthickness=1, **kwargs)

        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self.r = size * 0.38

        self.display_angle = 0.0
        self.zero_offset = 0.0  # 🔥 NUEVO

        self.callback = None
        self.grid_step = 10

        self.bind("<Button-1>", self.on_mouse)
        self.bind("<B1-Motion>", self.on_mouse)

        self.draw_dial()

    def set_callback(self, fn):
        self.callback = fn

    def set_angle(self, angle_deg: float):
        self.display_angle = normalize_360(angle_deg)
        self.draw_dial()

    def set_grid(self, step):
        self.grid_step = step
        self.draw_dial()

    def set_zero_here(self):
        # guardar estado actual
        current_angle = self.display_angle

        # 🔥 recalcular offset correctamente
        self.zero_offset = normalize_360(self.zero_offset + current_angle)

        # 🔥 ahora este punto es el nuevo cero
        self.display_angle = 0.0

        self.draw_dial()
    def on_mouse(self, event):
        dx = event.x - self.cx
        dy = self.cy - event.y

        if dx == 0 and dy == 0:
            return

        ang = math.degrees(math.atan2(dy, dx))
        ang = normalize_360(ang)

        # 🔥 corregir con offset
        logical_angle = normalize_360(ang - self.zero_offset)

        self.display_angle = logical_angle
        self.draw_dial()

        if self.callback:
            self.callback(logical_angle)

    def draw_dial(self):
        self.delete("all")

        # círculo base
        self.create_oval(
            self.cx - self.r, self.cy - self.r,
            self.cx + self.r, self.cy + self.r,
            width=2
        )

        step = self.grid_step
        label_step = 30

        # =========================
        # 1) GRID FINO (dinámico)
        # =========================
        for deg in range(0, 360, step):
            rad = math.radians(deg + self.zero_offset)

            x1 = self.cx + (self.r - 8) * math.cos(rad)
            y1 = self.cy - (self.r - 8) * math.sin(rad)

            x2 = self.cx + (self.r + 5) * math.cos(rad)
            y2 = self.cy - (self.r + 5) * math.sin(rad)

            self.create_line(x1, y1, x2, y2, width=1)


        # =========================
        # 2) MARCAS + NÚMEROS (FIJOS)
        # =========================
        for deg in range(0, 360, label_step):
            rad = math.radians(deg + self.zero_offset)

            x1 = self.cx + (self.r - 10) * math.cos(rad)
            y1 = self.cy - (self.r - 10) * math.sin(rad)

            x2 = self.cx + (self.r + 12) * math.cos(rad)
            y2 = self.cy - (self.r + 12) * math.sin(rad)

            # línea gruesa
            self.create_line(x1, y1, x2, y2, width=3)

            # texto
            tx = self.cx + (self.r + 32) * math.cos(rad)
            ty = self.cy - (self.r + 32) * math.sin(rad)

            self.create_text(tx, ty, text=str(deg), font=("Arial", 10, "bold"))

        # flecha con offset
        rad = math.radians(self.display_angle + self.zero_offset)

        x = self.cx + (self.r - 18) * math.cos(rad)
        y = self.cy - (self.r - 18) * math.sin(rad)

        self.create_line(
            self.cx, self.cy, x, y,
            width=5,
            arrow=tk.LAST,
            arrowshape=(16, 20, 6),
            fill="red"
        )

        self.create_oval(x-6, y-6, x+6, y+6, fill="red", outline="")
        self.create_oval(self.cx - 4, self.cy - 4, self.cx + 4, self.cy + 4, fill="black")

        self.create_text(
            self.cx,
            self.cy + self.r + 45,
            text=f"Posición actual: {self.display_angle:.1f}°",
            font=("Arial", 11, "bold")
        )

    def reset_zero(self):
        self.zero_offset = 0.0
        self.display_angle = 0.0
        self.draw_dial()


class StepperGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Control angular ESP32 Stepper")
        self.geometry("950x900")

        self.ser = None

        self.port_var = tk.StringVar(value="/dev/ttyUSB0")
        self.angle_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="Desconectado")

        self.grid_step = tk.IntVar(value=10)

        self.realtime_enabled = tk.BooleanVar(value=True)
        self.last_send_time = 0.0
        self.min_send_interval = 0.05

        self.build_ui()

    def build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Puerto:").pack(side="left")
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, values=list_ports(), width=22)
        self.port_combo.pack(side="left", padx=5)

        ttk.Button(top, text="Refrescar", command=self.refresh_ports).pack(side="left")
        ttk.Button(top, text="Conectar", command=self.connect_serial).pack(side="left")
        ttk.Button(top, text="Desconectar", command=self.disconnect_serial).pack(side="left")

        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=15)

        dial_frame = ttk.LabelFrame(self, text="Desplaza el selector angular", padding=10)
        dial_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top_controls = ttk.Frame(dial_frame)
        top_controls.pack()

        self.dial = AngleDial(dial_frame, size=580)
        self.dial.pack(expand=True)
        self.dial.set_callback(self.on_dial_changed)

        ctrl = ttk.LabelFrame(self, text="Control", padding=10)
        ctrl.pack(fill="x", padx=10, pady=10)

        row1 = ttk.Frame(ctrl)
        row1.pack(fill="x", pady=5)

        ttk.Label(row1, text="Ángulo:").pack(side="left")

        # ENTRY MODIFICADO (ENTER)
        angle_entry = ttk.Entry(row1, textvariable=self.angle_var, width=10)
        angle_entry.pack(side="left", padx=6)
        angle_entry.bind("<Return>", lambda event: self.goto_angle())

        ttk.Button(row1, text="Ir a ángulo", command=self.goto_angle).pack(side="left")
        ttk.Button(row1, text="HOME", command=self.send_home).pack(side="left")
        ttk.Button(row1, text="RESET", command=self.reset_system).pack(side="left")

        row2 = ttk.Frame(ctrl)
        row2.pack(fill="x", pady=5)

        ttk.Label(row2, text="Grid:").pack(side="left", padx=10)
        combo = ttk.Combobox(row2, textvariable=self.grid_step, values=[1, 2, 5, 10], width=5)
        combo.pack(side="left")

        self.grid_step.trace_add("write", self.on_grid_change)

    def on_grid_change(self, *args):
        self.dial.set_grid(self.grid_step.get())

    def refresh_ports(self):
        self.port_combo["values"] = list_ports()

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.port_var.get(), BAUD, timeout=1)
            time.sleep(2)
            self.status_var.set("Conectado")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def disconnect_serial(self):
        if self.ser:
            self.ser.close()
        self.status_var.set("Desconectado")

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())

    def maybe_send_angle(self, angle):
        if not self.realtime_enabled.get():
            return
        if not (self.ser and self.ser.is_open):
            return

        now = time.time()
        if (now - self.last_send_time) < self.min_send_interval:
            return

        self.send_command(f"GOTO {round(angle,2)}")
        self.last_send_time = now

    def on_dial_changed(self, angle):
        step = self.grid_step.get()
        snapped = round(angle / step) * step

        self.angle_var.set(f"{snapped:.1f}")
        self.dial.set_angle(snapped)

        self.maybe_send_angle(snapped)

    def goto_angle(self):
        try:
            angle = float(self.angle_var.get())
            self.dial.set_angle(angle)
            self.send_command(f"GOTO {angle}")
        except ValueError:
            messagebox.showerror("Error", "Ángulo inválido")

    def send_home(self):
        self.send_command("HOME")

        # redefinir el cero en la posición actual
        self.dial.set_zero_here()

        # actualizar UI (opcional)
        self.angle_var.set("0")

    def reset_system(self):
        self.dial.reset_zero()
        self.angle_var.set("0")

        # 🔥 primero resetear referencia en ESP32
        self.send_command("RESET")

        # 🔥 luego mover físicamente al cero real
        time.sleep(0.05)
        self.send_command("GOTO 0")

if __name__ == "__main__":
    app = StepperGUI()
    app.mainloop()