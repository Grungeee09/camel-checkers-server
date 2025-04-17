import json
import os
import re
import shutil
import string
import sys
import threading
import time
from tkinter.messagebox import showerror, showinfo, askyesno
from hashlib import sha256
import customtkinter as ctk
import requests as rq
from checkers import Checkers

__local__: bool = True
__version__: str = "1.0"

site = "https://camel-time-server.onrender.com" if not __local__ else "http://127.0.0.1:8000"


class Menu(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.geometry("520x350")
        self.title("Camel checkers")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.in_queue: bool = False
        self.account: dict[str, str] | None = None
        self.checkers: Checkers | None = None
        self.id: int | None = None

        self.loading_root: ctk.CTkToplevel | None = None
        self.login_root: ctk.CTkToplevel | None = None
        self.register_root: ctk.CTkToplevel | None = None
        self.settings_root: ctk.CTkToplevel | None = None
        self.account_root: ctk.CTkToplevel | None = None
        self.code_root: ctk.CTkToplevel | None = None
        self.queue_root: ctk.CTkToplevel | None = None

        self.small_font = ctk.CTkFont("Segoe UI", 12, "bold")
        self.default_font = ctk.CTkFont("Segoe UI")
        self.big_font = ctk.CTkFont("Segoe UI", 21, "bold")

        root_frame = ctk.CTkFrame(self, fg_color="#242424")
        root_frame.pack_propagate(False)
        root_frame.pack(expand=True, fill=ctk.BOTH)

        left_side = ctk.CTkFrame(root_frame, fg_color="#242424", width=175)
        left_side.pack_propagate(False)
        left_side.pack(side=ctk.LEFT, fill=ctk.BOTH)

        ctk.CTkButton(left_side, text="Settings", font=self.default_font, height=30, command=self.open_settings
                      ).pack(pady=(145, 10))
        ctk.CTkButton(left_side, text="Accounts", font=self.default_font, height=30, command=self.open_account_root
                      ).pack(pady=(0, 100))
        ctk.CTkLabel(left_side, text=f"version {__version__}", font=self.small_font,
                     text_color="#949494").pack(anchor=ctk.W, padx=10)

        right_side = ctk.CTkFrame(root_frame, height=330, width=335)
        right_side.pack_propagate(False)
        right_side.pack(side=ctk.RIGHT, padx=(0, 10))

        ctk.CTkLabel(right_side, text="Camel Checkers", font=("Segoe UI", 25, "bold")).pack(pady=(35, 0), padx=20)
        self.play_button = ctk.CTkButton(right_side, text="Play", font=("Segoe UI", 20), command=self.enter_queue,
                                         height=40, width=255, state=ctk.DISABLED, text_color_disabled="#ffffff",
                                         fg_color="#545454")
        self.play_button.pack(pady=(80, 0))

        self.account_label = ctk.CTkLabel(right_side, text="to play, first log into your account.",
                                          text_color="#949494", font=self.small_font)
        self.account_label.pack(pady=5)
        threading.Thread(target=self.init_account, args=(True,), daemon=True).start()

    def on_close(self):
        if self.in_queue:
            if askyesno("Confirmation",
                        "Are you sure you want to quit the program while you are in the queue?"):
                self.do_request(endpoint="/leave_queue", json=self.account, button_to_deactivate=self.play_button,
                                background=True)
                self.destroy()
        else:
            self.destroy()

    def all_roots(self) -> list:
        return [self.loading_root, self.register_root, self.settings_root, self.account_root,
                self.code_root, self.login_root, self.queue_root]

    def start_loading(self) -> None:
        if self.loading_root:
            return

        def animate() -> None:
            if self.loading_root:
                label_text = text.cget("text")
                if label_text == "Loading...":
                    text.configure(text="Loading")
                else:
                    text.configure(text=label_text + ".")
                self.after(200, animate)

        self.loading_root = ctk.CTkToplevel()
        self.loading_root.title("Loading")
        self.loading_root.geometry("220x180")
        self.loading_root.attributes("-topmost", True)
        self.loading_root.resizable(False, False)

        text = ctk.CTkLabel(self.loading_root, text="Loading", font=self.big_font)
        text.pack(pady=(70, 40))

        ctk.CTkLabel(self.loading_root, text="Requests can take up to a minute.", text_color="#949494",
                     font=self.small_font).pack()

        self.after(350, animate)

    def open_settings(self) -> None:
        def on_close() -> None:
            self.settings_root.destroy()
            self.settings_root = None

        if any(self.all_roots()):
            return
        self.settings_root = ctk.CTkToplevel(self)

        self.settings_root.geometry("300x280")
        self.settings_root.title("Settings")
        self.settings_root.resizable(False, False)
        self.settings_root.attributes("-topmost", True)
        self.settings_root.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkLabel(self.settings_root, text='Not implemented yet', font=self.default_font).pack(pady=120)

    def open_account_root(self) -> None:
        def on_close() -> None:
            self.account_root.destroy()
            self.account_root = None

        def logout() -> None:
            self.account_root.attributes("-topmost", False)

            if askyesno("Logout", "Are you sure you want to log out of the account?"):
                self.update_data(None, None)
                on_close()
                self.open_account_root()
            else:
                self.account_root.attributes("-topmost", True)

        if any(self.all_roots()):
            return

        self.account_root = ctk.CTkToplevel(self)

        self.account_root.geometry("300x280")
        self.account_root.title("Account")
        self.account_root.resizable(False, False)
        self.account_root.attributes("-topmost", True)
        self.account_root.protocol("WM_DELETE_WINDOW", on_close)

        if not self.account:
            ctk.CTkButton(self.account_root, text="Register", font=self.default_font, command=self.open_register_root,
                          height=30).pack(pady=(120, 90))
            login_label = ctk.CTkLabel(self.account_root, text="if you already have an account: login",
                                       font=self.small_font, cursor="hand2", text_color="#949494")
            login_label.bind("<Button-1>", self.open_login_root)
            login_label.pack()
        else:
            ctk.CTkLabel(self.account_root, text=f"Current account: {self.account["nickname"]}",
                         font=self.default_font).pack(pady=(100, 10))

            ctk.CTkButton(self.account_root, text="Logout", font=self.default_font, command=logout,
                          height=30).pack()

    def open_register_root(self) -> None:
        def continue_() -> None:
            nickname: str = nickname_entry.get()
            password: str = password_entry.get()
            email: str = email_entry.get()

            check: str | bool = check_all(nickname, password, email)

            if isinstance(check, str):
                showerror("Error", check)
                return

            json: dict = {"nickname": nickname, "password": hash_password(password), "email": email}

            code, response = self.do_request(endpoint="/start_registration", json=json,
                                             root_to_lower=self.register_root,
                                             button_to_deactivate=continue_button)

            if code == 200:
                response_json: dict = response.json()

                showinfo("Info", "Email sent successfully!")
                self.id = response_json["id"]
                self.register_root.withdraw()
                self.open_code_root()

        def on_close() -> None:
            self.register_root.destroy()
            self.register_root = None
            self.open_account_root()

        if self.account_root is not None:
            self.account_root.destroy()
            self.account_root = None

        self.register_root = ctk.CTkToplevel(self)

        self.register_root.geometry("300x250")
        self.register_root.title("Register")
        self.register_root.resizable(False, False)
        self.register_root.attributes("-topmost", True)
        self.register_root.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkLabel(self.register_root, text="Registration", font=("Segue UI", 21, "bold")).pack(pady=20)

        nickname_frame = ctk.CTkFrame(self.register_root, width=280, height=30)
        nickname_frame.pack_propagate(False)
        nickname_frame.pack(pady=(0, 10))

        ctk.CTkLabel(nickname_frame, text="Nickname: ", font=self.default_font).pack(side=ctk.LEFT, padx=5)

        nickname_entry = ctk.CTkEntry(nickname_frame, width=190)
        nickname_entry.pack(side=ctk.RIGHT, padx=5)

        password_frame = ctk.CTkFrame(self.register_root, width=280, height=30)
        password_frame.pack_propagate(False)
        password_frame.pack(pady=(0, 10))

        ctk.CTkLabel(password_frame, text="Password: ", font=self.default_font).pack(side=ctk.LEFT, padx=5)

        password_entry = ctk.CTkEntry(password_frame, width=190, show="*")
        password_entry.pack(side=ctk.RIGHT, padx=5)
        password_entry.bind("<Enter>", lambda _: password_entry.configure(show=""))
        password_entry.bind("<Leave>", lambda _: password_entry.configure(show="*"))

        email_frame = ctk.CTkFrame(self.register_root, width=280, height=30)
        email_frame.pack_propagate(False)
        email_frame.pack(pady=(0, 20))

        ctk.CTkLabel(email_frame, text="Email: ", font=self.default_font).pack(side=ctk.LEFT, padx=5)

        email_entry = ctk.CTkEntry(email_frame, width=190)
        email_entry.pack(side=ctk.RIGHT, padx=5)

        continue_button = ctk.CTkButton(self.register_root, text="Send code", font=self.default_font,
                                        command=lambda: threading.Thread(target=continue_, daemon=True).start())
        continue_button.pack()

    def open_code_root(self) -> None:
        def on_close() -> None:
            self.code_root.destroy()
            self.code_root = None
            self.register_root.deiconify()

        def validate_input(text: str) -> bool:
            validation: bool = (text.isdigit() and len(text) <= 6) or text == "" or text == "Your code..."

            if not validation:
                if sys.platform == "win32":
                    import winsound
                    winsound.MessageBeep()
                else:
                    self.bell()
            elif len(text) == 6:
                confirm_button.configure(state=ctk.NORMAL)
            elif len(text) < 6:
                confirm_button.configure(state=ctk.DISABLED)

            return validation

        def confirm() -> None:
            json: dict = {"id": self.id, "code": code_entry.get()}

            code, response = self.do_request(endpoint="/finish_registration", json=json, root_to_lower=self.code_root,
                                             button_to_deactivate=confirm_button)

            if code == 200:
                showinfo("Info", "Account created successfully!")
                on_close()
                self.register_root.destroy()
                self.register_root = None
                self.open_account_root()

        self.code_root = ctk.CTkToplevel(self)
        self.code_root.title("Code confirmation")
        self.code_root.geometry("270x150")
        self.code_root.resizable(False, False)
        self.code_root.attributes("-topmost", True)
        self.code_root.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkButton(self.code_root, text="<- Back", width=35, command=on_close).pack(padx=10, pady=10, anchor=ctk.W)

        validate_command = self.code_root.register(validate_input)

        code_entry = ctk.CTkEntry(self.code_root, placeholder_text="Your code...", width=180, validate="key",
                                  validatecommand=(validate_command, "%P"))
        code_entry.pack(pady=10)

        confirm_button = ctk.CTkButton(self.code_root, text="Confirm",
                                       command=lambda: threading.Thread(target=confirm, daemon=True).start(),
                                       state=ctk.DISABLED)
        confirm_button.pack(pady=10)

    def open_login_root(self, _=None) -> None:
        def login() -> None:
            nickname: str = nickname_entry.get()
            password: str = password_entry.get()

            check: str | bool = check_all(nickname, password)

            if isinstance(check, str):
                showerror("Error", check)
                return

            json: dict = {"nickname": nickname, "password": hash_password(password)}

            code, response = self.do_request(endpoint="/login", json=json, root_to_lower=self.login_root,
                                             button_to_deactivate=continue_button)

            if code == 200:
                response_json: dict = response.json()
                showinfo("Info", response_json["message"])

                self.update_data(nickname, hash_password(password), False)
                on_close()

        def on_close() -> None:
            self.login_root.destroy()
            self.login_root = None
            self.open_account_root()

        if self.account_root is not None:
            self.account_root.destroy()
            self.account_root = None

        self.login_root = ctk.CTkToplevel(self)

        self.login_root.geometry("300x210")
        self.login_root.title("Log in")
        self.login_root.resizable(False, False)
        self.login_root.attributes("-topmost", True)

        def on_close() -> None:
            self.login_root.destroy()
            self.login_root = None
            self.open_account_root()

        ctk.CTkLabel(self.login_root, text="Authentication", font=("Segue UI", 21, "bold")).pack(pady=20)

        nickname_frame = ctk.CTkFrame(self.login_root, width=280, height=30)
        nickname_frame.pack_propagate(False)
        nickname_frame.pack(pady=(0, 10))

        ctk.CTkLabel(nickname_frame, text="Nickname: ", font=self.default_font).pack(side=ctk.LEFT, padx=5)

        nickname_entry = ctk.CTkEntry(nickname_frame, width=190)
        nickname_entry.pack(side=ctk.RIGHT, padx=5)

        password_frame = ctk.CTkFrame(self.login_root, width=280, height=30)
        password_frame.pack_propagate(False)
        password_frame.pack()

        ctk.CTkLabel(password_frame, text="Password: ", font=self.default_font).pack(side=ctk.LEFT, padx=5)

        password_entry = ctk.CTkEntry(password_frame, width=190, show="*")
        password_entry.pack(side=ctk.RIGHT, padx=5)
        password_entry.bind("<Enter>", lambda _: password_entry.configure(show=""))
        password_entry.bind("<Leave>", lambda _: password_entry.configure(show="*"))

        continue_button = ctk.CTkButton(self.login_root, text="Log in", font=self.default_font,
                                        command=lambda: threading.Thread(target=login, daemon=True).start())
        continue_button.pack(pady=20)

    def enter_queue(self) -> None:
        code, response = self.do_request(endpoint="/join_queue", json=self.account,
                                         button_to_deactivate=self.play_button)

        if code == 200:
            self.in_queue = True
            self.wait_in_queue()
        elif code == 400:
            self.update_data(None, None)

    def wait_in_queue(self) -> None:
        def animate() -> None:
            if self.queue_root:
                label_text = main_label.cget("text")
                if label_text == "Searching game...":
                    main_label.configure(text="Searching game")
                else:
                    main_label.configure(text=label_text + ".")
                self.after(600, animate)

        def update_time(start_time: float) -> None:
            if self.queue_root:
                code, response = self.do_request(endpoint="/update_queue", json=self.account,
                                                 button_to_deactivate=self.play_button, background=True)

                if code == 200:
                    response = response.json()

                    if response["game_id"] is not None:
                        pass
                    else:
                        elapsed = int(time.time() - start_time)
                        minutes, seconds = divmod(elapsed, 60)
                        time_label.configure(text=f"Searching for: {minutes:02}:{seconds:02}")

                        self.after(1000, lambda: update_time(start_time))
                elif code == 400:
                    on_close(False)

        def on_close(confirmation: bool = True) -> None:
            if not confirmation or askyesno("Confirmation", "Are you sure you want to leave the queue?"):
                self.do_request(endpoint="/leave_queue", json=self.account, button_to_deactivate=self.play_button,
                                background=True)

                self.queue_root.destroy()
                self.queue_root = None
                self.in_queue = False

        if any(self.all_roots()):
            return

        self.queue_root = ctk.CTkToplevel()
        self.queue_root.title("Queue")
        self.queue_root.geometry("220x160")
        self.queue_root.attributes("-topmost", True)
        self.queue_root.resizable(False, False)
        self.queue_root.protocol("WM_DELETE_WINDOW", on_close)

        main_label = ctk.CTkLabel(self.queue_root, text="Searching game", font=self.big_font)
        main_label.pack(pady=(50, 0))

        time_label = ctk.CTkLabel(self.queue_root, text="Searching for: 00:00", font=self.small_font,
                                  text_color="#949494")
        time_label.pack(pady=(0, 0))

        cancel_button = ctk.CTkButton(self.queue_root, text="Cancel", font=self.small_font, width=30,
                                      command=lambda: on_close(False))
        cancel_button.pack(pady=(15, 0))

        self.after(600, animate)
        update_time(time.time())

    def do_request(self, endpoint: str, json: dict, root_to_lower: ctk.CTkToplevel | None = None,
                   button_to_deactivate: ctk.CTkButton | None = None,
                   background: bool = False) -> tuple[int, rq.Response | None]:
        error_message: None | str = None

        if root_to_lower:
            root_to_lower.attributes("-topmost", False)
        if button_to_deactivate:
            button_to_deactivate.configure(state=ctk.DISABLED)

        if not background:
            self.start_loading()

        try:
            response = rq.post(f"{site}{endpoint}", json=json)
            status_code = response.status_code

            if status_code != 200:
                error_message = response.json()["detail"]
                response = None

        except Exception as e:
            if isinstance(e, rq.exceptions.ConnectionError):
                error_message = ("Failed to connect to the server. "
                                 "You may not have an internet connection or the server may be down.")
            elif isinstance(e, rq.exceptions.JSONDecodeError):
                error_message = "Failed to connect to the server. Most likely the server is currently down."
            else:
                error_message = f"An error ({type(e)}) occurred: \n{e}"

            response = None
            status_code = 400
        finally:
            if not background:
                self.loading_root.destroy()
                self.loading_root = None

        if error_message:
            showerror("Error", error_message)

        if root_to_lower:
            root_to_lower.attributes("-topmost", True)
        if button_to_deactivate:
            button_to_deactivate.configure(state=ctk.NORMAL)

        return status_code, response

    def update_data(self, nickname: str | None, password: str | None, with_request: bool = True) -> None:
        self.init_data()

        new_data: dict = {"nickname": nickname, "password": password}

        with open("data.json", "w") as file:
            json.dump(new_data, file, indent=4)

        self.init_account(with_request)

    def init_account(self, with_request: bool) -> None:
        self.init_data()

        with open("data.json", "r") as file:
            data: dict = json.load(file)

        nickname: str | None = data["nickname"]
        password: str | None = data["password"]

        if all([nickname, password]):
            json_: dict = {"nickname": nickname, "password": password}

            code, response = self.do_request(endpoint="/login", json=json_) if with_request else (200, None)

            if code == 200:
                self.account = json_
                self.play_button.configure(state=ctk.NORMAL, fg_color="#1f6aa5")
                self.account_label.configure(text=f"Account: {nickname}")
            else:
                os.remove("data.json")
                self.init_data()
        else:
            self.account = None
            self.play_button.configure(state=ctk.DISABLED, fg_color="#545454")
            self.account_label.configure(text="to play, first log into your account.")

    def init_data(self) -> None:
        if os.path.exists("data.json"):
            if os.path.isfile("data.json"):
                try:
                    with open("data.json", "r") as file:
                        data: dict = json.load(file)

                    if any(key not in data or not isinstance(data[key], str) for key in ("nickname", "password")):
                        os.remove("data.json")
                        self.init_data()

                except json.decoder.JSONDecodeError:
                    os.remove("data.json")
                    self.init_data()
            else:
                shutil.rmtree("data.json")
                self.init_data()
        else:
            data: dict = {"nickname": None, "password": None}

            with open("data.json", "w") as file:
                json.dump(data, file, indent=4)


def check_all(username: str, password: str, email: str | None = None) -> str | bool:
    if username == "":
        return "The username input field is empty"
    if password == "":
        return "The password input field is empty"

    for symbol in username:
        if symbol not in string.ascii_letters + string.digits + "_-":
            return "Unsupported characters in username"
    if len(username) < 4:
        return "The length of the username must be longer than 3 characters"
    elif len(username) > 20:
        return "Username length should not be longer than 20 characters"

    for symbol in password:
        if symbol not in string.ascii_letters + string.digits + "_-":
            return "Unsupported characters in password"
    if len(password) < 5:
        return "The length of the password must be longer than 4 characters"
    elif len(username) > 25:
        return "Password length should not be longer than 25 characters"

    if email is not None:
        if email == "":
            return "The email input field is empty"

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return "Incorrect email"

    return True


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


if __name__ == '__main__':
    Menu().mainloop()
