import customtkinter as ctk
import requests as rq
import re
import sys
import string
import threading
from tkinter.messagebox import showerror, showinfo

__version__ = "1.0"
site = "http://127.0.0.1:8000"
# https://camel-time-server.onrender.com


class Menu(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.geometry("520x350")
        self.title("Camel checkers")
        self.resizable(False, False)

        self.id: None | int = None
        self.response: None | rq.Response = None
        self.loading_root: None | ctk.CTkToplevel = None
        self.register_root: None | ctk.CTkToplevel = None
        self.settings_root: None | ctk.CTkToplevel = None
        self.account_root: None | ctk.CTkToplevel = None
        self.code_root: None | ctk.CTkToplevel = None

        self.all_roots: list = [self.loading_root, self.register_root,
                                self.settings_root, self.account_root, self.code_root]

        self.small_font = ctk.CTkFont("Segoe UI", 12, "bold")
        self.default_font = ctk.CTkFont("Segoe UI")
        self.big_font = ctk.CTkFont("Segoe UI", 21, "bold")

        ctk.CTkButton(self, text="Settings", font=self.default_font, height=30, command=self.open_settings
                      ).place(x=15, y=140)
        ctk.CTkButton(self, text="Accounts", font=self.default_font, height=30, command=self.open_account_root
                      ).place(x=15, y=180)
        ctk.CTkLabel(self, text=f"version {__version__}", font=self.small_font,
                     text_color="#949494").place(x=15, y=320)

        frame = ctk.CTkFrame(self, height=330, width=335)
        frame.place(x=175, y=10)

        ctk.CTkLabel(frame, text="Camel Checkers", font=("Segoe UI", 25, "bold")).place(x=70, y=30)
        ctk.CTkButton(frame, text="Play", font=("Segoe UI", 20), command=self.play, height=40,
                      width=255).place(x=40, y=150)
        ctk.CTkLabel(frame, text="to play, first log into your account.", text_color="#949494", font=self.small_font
                     ).place(x=70, y=190)

    def start_loading(self) -> None:
        if self.loading_root:
            return

        def animate() -> None:
            if self.loading_root:
                label_text = text.cget("text")
                if label_text == "Loading...":
                    text.configure(text="Loading")
                else:
                    text.configure(text=label_text+".")
                self.after(200, animate)

        self.loading_root = ctk.CTkToplevel()
        self.loading_root.geometry("150x120")
        self.loading_root.attributes("-topmost", True)
        self.loading_root.resizable(False, False)

        text = ctk.CTkLabel(self.loading_root, text="Loading", font=self.big_font)
        text.pack(pady=(40, 0))

        self.after(350, animate)

    def open_settings(self) -> None:
        def on_close() -> None:
            self.settings_root.destroy()
            self.settings_root = None

        if any(self.all_roots):
            return
        self.settings_root = ctk.CTkToplevel(self)

        self.settings_root.geometry("300x280")
        self.settings_root.title("Settings")
        self.settings_root.resizable(False, False)
        self.settings_root.attributes("-topmost", True)
        self.settings_root.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkLabel(self.settings_root, text='Not implemented yet').pack(pady=120)

    def open_account_root(self) -> None:
        def on_close() -> None:
            self.account_root.destroy()
            self.account_root = None

        if any(self.all_roots):
            return

        self.account_root = ctk.CTkToplevel(self)

        self.account_root.geometry("300x280")
        self.account_root.title("Account")
        self.account_root.resizable(False, False)
        self.account_root.attributes("-topmost", True)
        self.account_root.protocol("WM_DELETE_WINDOW", on_close)

        ctk.CTkButton(self.account_root, text="Register", font=self.default_font, command=self.open_register_root,
                      height=30).pack(pady=(120, 90))
        login_label = ctk.CTkLabel(self.account_root, text="if you already have an account: login",
                                   font=self.small_font, cursor="hand2", text_color="#949494")
        login_label.bind("<Button-1>", self.login)
        login_label.pack()

    def open_register_root(self) -> None:
        def continue_() -> None:
            nickname: str = nickname_entry.get()
            password: str = password_entry.get()
            email: str = email_entry.get()
            json: dict = {"nickname": nickname, "password": password, "email": email}
            check: str | bool = check_all(nickname, password, email)

            if isinstance(check, str):
                showerror("Error", check)
                return

            response: rq.Response | None = self.do_request(endpoint="/start_registration", json=json,
                                                           root_to_lower=self.register_root,
                                                           button_to_deactivate=continue_button)

            if response is not None:
                response_json: dict = response.json()

                showinfo("Info", response_json["message"])
                self.id = response_json["id"]
                self.register_root.withdraw()
                self.open_code_root()

        def on_close() -> None:
            self.register_root.destroy()
            self.register_root = None
            self.open_account_root()

        if self.register_root is not None:
            return
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

        continue_button = ctk.CTkButton(self.register_root, text="Send code", font=self.default_font, command=lambda:
                                        threading.Thread(target=continue_, daemon=True).start())
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

            response: rq.Response | None = self.do_request(endpoint="/finish_registration", json=json,
                                                           root_to_lower=self.code_root,
                                                           button_to_deactivate=confirm_button)

            if response is not None:
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

        confirm_button = ctk.CTkButton(self.code_root, text="Confirm", command=confirm, state=ctk.DISABLED)
        confirm_button.pack(pady=10)

    def login(self, _=None) -> None:
        pass

    def play(self) -> None:
        pass

    def do_request(self, endpoint: str, json: dict, root_to_lower: ctk.CTkToplevel | None = None,
                   button_to_deactivate: ctk.CTkButton | None = None) -> None | rq.Response:
        error_message: None | str = None

        if root_to_lower:
            root_to_lower.attributes("-topmost", False)
        if button_to_deactivate:
            button_to_deactivate.configure(state=ctk.DISABLED)

        self.start_loading()
        try:
            self.response = rq.post(f"{site}{endpoint}", json=json)

            if self.response.status_code != 200:
                error_message = self.response.json()["detail"]
                self.response = None

        except Exception as e:
            if type(e) in [rq.exceptions.ConnectionError]:
                error_message = (f"Failed to connect to the server. "
                                 f"You may not have an internet connection or the server may be down.")
            else:
                error_message = f"An error ({type(e)}) occurred: \n{e}"

            self.response = None

        finally:
            self.loading_root.destroy()
            self.loading_root = None

        if error_message:
            showerror("Error", error_message)

        if root_to_lower:
            root_to_lower.attributes("-topmost", True)
        if button_to_deactivate:
            button_to_deactivate.configure(state=ctk.NORMAL)

        return self.response


def check_all(username: str, password: str, email: str) -> str | bool:
    if username == "":
        return "The username input field is empty"
    if password == "":
        return "The password input field is empty"
    if email == "":
        return "The email input field is empty"

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
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return "Incorrect email"
    return True


if __name__ == '__main__':
    Menu().mainloop()
