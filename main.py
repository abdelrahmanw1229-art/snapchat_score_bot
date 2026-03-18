from colorama import Fore
import pyautogui, time, sys, threading
# Try to import tkinter for the GUI; if unavailable, set tk to None
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None

# The `keyboard` library on macOS requires administrator privileges and will
# raise OSError when trying to listen. Do NOT import or use it on macOS by
# default — fall back to Enter-based prompts instead.
if sys.platform == "darwin":
    keyboard = None
    KEYBOARD_AVAILABLE = False
else:
    try:
        import keyboard
        KEYBOARD_AVAILABLE = True
    except Exception:
        keyboard = None
        KEYBOARD_AVAILABLE = False

class snapchat:
    
    def __init__(self):
        self.sent_snaps = 0
        # delay between individual snaps (seconds)
        self.delay = 0.3
        self.num_positions = 0
        self.positions = []
        # paused flag controlled by GUI or fallback
        self.paused = False
        self.stop_event = threading.Event()
        self.sending_thread = None
                        
    def get_positions(self):
        # Capture exactly `self.num_positions` positions into a list
        self.positions = []
        for i in range(1, self.num_positions + 1):
            self.print_console(f"Move your mouse to position {i}, then press F (or Enter as fallback)")
            self.wait_for_key("f")
            self.positions.append(pyautogui.position())
            time.sleep(0.5)

    def wait_for_key(self, key="f"):
        if KEYBOARD_AVAILABLE:
            try:
                while True:
                    try:
                        if keyboard.is_pressed(key):
                            return
                    except Exception:
                        break
                    time.sleep(0.05)
            except Exception:
                pass
        input(f"Press Enter to continue (expected key: {key})...")

    # --- GUI -------------------------------------------------
    def setup_gui(self):
        if tk is None:
            print("Tkinter not available — GUI cannot be started.")
            return

        print("[debug] starting GUI...")
        try:
            self.root = tk.Tk()
        except Exception as e:
            print(f"[debug] tk.Tk() raised: {e}")
            raise
        self.root.title("Snapscore Control")
        # set an explicit geometry and center on screen to avoid off-screen windows
        try:
            w, h = 600, 360
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.update()
            print("[debug] root created and geometry set")
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes('-topmost', True)
                # clear topmost after a short delay
                self.root.after(500, lambda: self.root.attributes('-topmost', False))
                print("[debug] attempted to lift/deiconify window")
            except Exception as e:
                print(f"[debug] window lift/deiconify error: {e}")
            # hotkey registration will be set up after GUI widgets are created
        except Exception as e:
            print(f"[debug] window init/update error: {e}")

        frm = ttk.Frame(self.root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        # Make layout responsive so fullscreen looks good
        try:
            self.root.rowconfigure(0, weight=1)
            self.root.columnconfigure(0, weight=1)
            frm.rowconfigure(1, weight=1)  # listbox row
            for c in range(4):
                frm.columnconfigure(c, weight=1)
        except Exception:
            pass

        ttk.Label(frm, text="Number of positions:").grid(row=0, column=0, sticky="w")
        self.num_var = tk.IntVar(value=max(1, self.num_positions))
        self.num_spin = ttk.Spinbox(frm, from_=1, to=50, textvariable=self.num_var, width=5)
        self.num_spin.grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Delay (s):").grid(row=0, column=2, padx=(10,0))
        self.delay_var = tk.DoubleVar(value=self.delay)
        self.delay_entry = ttk.Entry(frm, textvariable=self.delay_var, width=6)
        self.delay_entry.grid(row=0, column=3, sticky="w")

        # Positions list and controls
        self.listbox = tk.Listbox(frm)
        self.listbox.grid(row=1, column=0, columnspan=4, pady=(8,0), sticky="nsew")

        # Show shortcut instruction
        ttk.Label(frm, text="Press 'r' to record current mouse position (global if available)").grid(row=4, column=0, columnspan=4, pady=(4,0), sticky="w")

        # Register global hotkeys if keyboard module is available, otherwise bind to window
        self._hotkey_handlers = []
        def bind_or_add(key, callback, local_event=None):
            if KEYBOARD_AVAILABLE:
                try:
                    h = keyboard.add_hotkey(key, lambda: callback())
                    self._hotkey_handlers.append(h)
                    print(f"[debug] registered global hotkey '{key}'")
                    return
                except Exception as e:
                    print(f"[debug] failed to register global hotkey '{key}': {e}")
            # fallback: bind to window keypress (works when window focused)
            try:
                if local_event is None:
                    # default to KeyPress-<char>
                    self.root.bind(f"<KeyPress-{key}>", lambda e: callback())
                else:
                    self.root.bind(local_event, lambda e: callback())
                print(f"[debug] bound local key '{key}' to window")
            except Exception as e:
                print(f"[debug] failed to bind local key '{key}': {e}")

        # record: 'r'
        bind_or_add('r', lambda: self._record_from_hotkey())
        # pause toggle: 'p'
        bind_or_add('p', lambda: self._toggle_pause_from_hotkey())
        # (no explicit resume hotkey; use 'p' toggle)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=2, column=0, columnspan=4, pady=8, sticky="ew")

        self.record_btn = ttk.Button(btn_frame, text="Record Position", command=self.record_position)
        self.record_btn.grid(row=0, column=0, padx=4)

        self.clear_btn = ttk.Button(btn_frame, text="Clear Positions", command=self.clear_positions)
        self.clear_btn.grid(row=0, column=1, padx=4)

        self.up_btn = ttk.Button(btn_frame, text="Move Up", command=self.move_up_selected)
        self.up_btn.grid(row=0, column=5, padx=4)

        self.down_btn = ttk.Button(btn_frame, text="Move Down", command=self.move_down_selected)
        self.down_btn.grid(row=0, column=6, padx=4)

        self.delete_btn = ttk.Button(btn_frame, text="Delete", command=self.delete_selected)
        self.delete_btn.grid(row=0, column=7, padx=4)

        self.start_btn = ttk.Button(btn_frame, text="Start Sending", command=self.start_sending)
        self.start_btn.grid(row=0, column=2, padx=4)

        self.pause_btn = ttk.Button(btn_frame, text="Pause", command=self.toggle_pause)
        self.pause_btn.grid(row=0, column=3, padx=4)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop_sending)
        self.stop_btn.grid(row=0, column=4, padx=4)

        # Status label
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(frm, textvariable=self.status_var).grid(row=3, column=0, columnspan=4, pady=(4,0), sticky="w")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def record_position(self):
        pos = pyautogui.position()
        self.positions.append(pos)
        self.num_positions = len(self.positions)
        self.update_listbox()

    def _record_from_hotkey(self):
        # schedule record_position on the GUI/main thread
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, self.record_position)
            else:
                self.record_position()
        except Exception:
            try:
                self.record_position()
            except Exception:
                pass

    def _toggle_pause_from_hotkey(self):
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, self.toggle_pause)
            else:
                self.toggle_pause()
        except Exception:
            try:
                self.toggle_pause()
            except Exception:
                pass


    def clear_positions(self):
        self.positions = []
        self.listbox.delete(0, tk.END)
        self.num_positions = 0
        self.update_listbox()

    def update_listbox(self):
        try:
            self.listbox.delete(0, tk.END)
            for i, pos in enumerate(self.positions, start=1):
                self.listbox.insert(tk.END, f"{i}: {pos}")
        except Exception:
            pass

    def delete_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            del self.positions[idx]
        except Exception:
            return
        self.update_listbox()
        # select the same index if possible
        if idx < len(self.positions):
            self.listbox.selection_set(idx)

    def move_up_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx <= 0:
            return
        self.positions[idx-1], self.positions[idx] = self.positions[idx], self.positions[idx-1]
        self.update_listbox()
        self.listbox.selection_set(idx-1)

    def move_down_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.positions)-1:
            return
        self.positions[idx+1], self.positions[idx] = self.positions[idx], self.positions[idx+1]
        self.update_listbox()
        self.listbox.selection_set(idx+1)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text=("Resume" if self.paused else "Pause"))
        self.status_var.set("Paused" if self.paused else "Running")

    def start_sending(self):
        # update delay and num_positions from UI
        try:
            self.delay = float(self.delay_var.get())
        except Exception:
            self.delay = 0.3
        if not self.positions:
            self.status_var.set("No positions recorded")
            return
        if self.sending_thread and self.sending_thread.is_alive():
            return
        self.stop_event.clear()
        self.paused = False
        self.pause_btn.config(text="Pause")
        self.sending_thread = threading.Thread(target=self._sending_loop, daemon=True)
        self.sending_thread.start()
        self.status_var.set("Sending...")

    def _sending_loop(self):
        while not self.stop_event.is_set():
            if self.paused:
                time.sleep(0.1)
                continue
            try:
                self.send_snap()
            except Exception as e:
                self.status_var.set(f"Error: {e}")
                break
            time.sleep(self.delay)
        self.status_var.set("Stopped")

    def stop_sending(self):
        self.stop_event.set()
        self.paused = False
        self.pause_btn.config(text="Pause")

    def _on_close(self):
        self.stop_sending()
        # remove global hotkeys if any
        if KEYBOARD_AVAILABLE and hasattr(self, '_hotkey_handlers'):
            try:
                for h in self._hotkey_handlers:
                    try:
                        keyboard.remove_hotkey(h)
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def start_control_gui(self):
        try:
            import tkinter as tk
        except Exception:
            # tkinter not available — skip GUI control
            return

        def toggle_pause():
            self.paused = not self.paused
            btn.config(text=("Resume" if self.paused else "Pause"))

        root = tk.Tk()
        root.title("SnapControl")
        btn = tk.Button(root, text="Pause", width=12, command=toggle_pause)
        btn.pack(padx=10, pady=10)
        try:
            root.mainloop()
        except Exception:
            pass
    
    def send_snap(self):
        # Use the captured positions list. Order is the order the user entered.
        if not self.positions:
            return

        # First position: single click
        pyautogui.moveTo(self.positions[0])
        pyautogui.click()

        # Second position: emulate original behaviour (7 clicks) if present
        if len(self.positions) >= 2:
            pyautogui.moveTo(self.positions[1])
            for _ in range(7):
                pyautogui.click()
                time.sleep(self.delay)

        # Remaining positions: single click each in order
        for pos in self.positions[2:]:
            pyautogui.moveTo(pos)
            pyautogui.click()
            time.sleep(0)

        # Update sent snaps counter (preserve original +7 when second position exists)
        if len(self.positions) >= 2:
            self.sent_snaps += 7
        else:
            self.sent_snaps += 1
       
    def print_console(self, arg, status = "Console"):
        print(f"\n       {Fore.WHITE}[{Fore.RED}{status}{Fore.WHITE}] {arg}")
    
    def main(self):
        print("Enter number of positions:")
        num_positions = int(input())
        self.num_positions = num_positions
        self.get_positions()
        self.print_console("Press F to start (or Enter as fallback)")
        shortcut_users = 0
        self.print_console("Go to your chats, then press F when you're ready.")
        time.sleep(0.2)
        self.wait_for_key("f")
        self.print_console("Sending snaps...")
        self.started_time = time.time()
        while True:
            try:
                if keyboard.is_pressed("p"):
                    break
            except Exception:
                pass
            # pause if GUI toggled pause
            while getattr(self, 'paused', False):
                time.sleep(0.1)
            self.send_snap()
            print(f"{Fore.WHITE}[{Fore.RED}Console{Fore.WHITE}] {Fore.GREEN}Sending snaps...")
            time.sleep(self.delay)
        self.print_console(f"Finished sending {self.sent_snaps} snaps.")
        
if __name__ == "__main__":
    app = snapchat()
    # If tkinter is available, start the GUI; otherwise fall back to console main
    print(f"[debug] tkinter available: {tk is not None}")
    if tk is not None:
        try:
            app.setup_gui()
        except Exception as e:
            print(f"[debug] GUI failed to start: {e}")
            print("Falling back to console mode.")
            app.main()
    else:
        app.main()