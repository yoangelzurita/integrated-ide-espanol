"""Utilidades de consola de salida para el IDE."""

import tkinter as tk
from tkinter import scrolledtext


class ConsolaSalida:
    """Wrapper thread-safe (vía root.after) sobre un ScrolledText."""

    def __init__(self, widget: scrolledtext.ScrolledText, root: tk.Tk):
        self.widget = widget
        self.root = root

    def limpiar(self):
        def _do():
            self.widget.config(state=tk.NORMAL)
            self.widget.delete("1.0", tk.END)

        self.root.after(0, _do)

    def escribir(self, texto: str, tag: str | None = None):
        def _do():
            self.widget.config(state=tk.NORMAL)
            if tag:
                self.widget.insert(tk.END, texto, tag)
            else:
                self.widget.insert(tk.END, texto)
            self.widget.see(tk.END)

        self.root.after(0, _do)

    def info(self, msg: str):
        self.escribir(f"[INFO] {msg}\n", "info")

    def exito(self, msg: str):
        self.escribir(f"[OK] {msg}\n", "ok")

    def error(self, msg: str):
        self.escribir(f"[ERROR] {msg}\n", "error")
