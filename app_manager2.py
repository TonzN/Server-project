from loads import *
from client.loads import *
import traceback
import client.client_manager as client


HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

def check_threads():
    print("Active threads:", threading.enumerate())
    list_running_coroutines()
   # debug_stuck_coroutines()
    check_zombie_threads()
  #  dump_stuck_thread()

def dump_stuck_thread():
    for thread in threading.enumerate():
        if thread.name.startswith("asyncio_"):
            print(f"\n🔍 Debugging {thread.name}...")

            for thread_id, frame in sys._current_frames().items():
                if thread.ident == thread_id:
                    print("🔍 Stack trace of stuck thread:")
                    traceback.print_stack(frame)

def check_zombie_threads():
    for thread in threading.enumerate():
        if thread.name.startswith("asyncio_") or thread.name.startswith("Thread-"):
            print(f"⚠️ Possible zombie thread detected: {thread.name} (Alive: {thread.is_alive()})")

def debug_stuck_coroutines():
    try:
        loop = asyncio.get_event_loop()
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
    
    except Exception as e:
        return

    if tasks:
        print(f"⚠️ {len(tasks)} stuck coroutine(s) found:")
        for task in tasks:
            print(f" - {task.get_coro()} (State: {task._state})")

    return tasks

def list_running_coroutines():
    try:
        loop = asyncio.get_event_loop()
        
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
    except Exception as e:
        print("no running courotines")
        return
    
    print(f"⚠️ {len(tasks)} running coroutine(s) detected:")

    for task in tasks:
        coro = task.get_coro()  # Get coroutine object
        print(f"🔹 Coroutine: {coro} (State: {task._state})")

        # Extract where the coroutine was created
        frames = traceback.extract_stack(coro.cr_frame)
        print("🔍 Origin trace:")
        for frame in frames[-5:]:  # Show last 5 calls
            print(f"  📌 {frame.filename}:{frame.lineno} in {frame.name}")
        print("-" * 50)

class RemoteSignal(QThread):
    signal = pyqtSignal(dict)

class Client_thread(QThread):
    login_signal = pyqtSignal()
    rec_stop = None
    heart_stop = None
    rec_thread = None
    heartbeat_thread = None
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.client_sock:
            try:
                self.client_sock.connect((HOST, PORT))
                print(f"Client connected.\n")
            except socket.timeout:
                print("Client timeout: attempted connecting for too long")
                return
            except Exception as e:
                print(f"Client did not connect: {e}\n")
                return  
            
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.run_client(self.client_sock, self.login_signal))
            finally:
                self.loop.close()
                print("closed thread socket")
                return

    async def run_client(self, client_sock, login_signal):
        config["client_sock"] = client_sock
        self.rec_thread = threading.Thread(target=client.receive_thread, args=(client_sock, self.rec_stop), daemon=True)
        self.rec_thread.start()

        try: 
            await asyncio.wait_for(asyncio.to_thread(client.receieve_events["join_protocol"].wait), timeout=5)
            token = await client.receieve_queue["join_protocol"].get()
            client.receieve_events["join_protocol"].clear()
            time.sleep(0.5) #artificial delay
            
            if token:
                login_signal.emit()
                config["token"] = token
                self.heartbeat_thread = threading.Thread(target=client.heartbeat, args=(client_sock, self.heart_stop, config["token"]), daemon=True)
                self.heartbeat_thread.start()
              
                await client.run_client(client_sock, self.heart_stop)
            else:
                print("token invalid")     
        except asyncio.TimeoutError:
            print("Timout waiting for join_protocol")
        
        finally:
            # Safely stop asyncio tasks
            print("Shutting down asyncio tasks...")
            loop = asyncio.get_event_loop()

            # Cancel all asyncio tasks
            tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            for task in tasks:
                task.cancel()

            # Wait for tasks to cancel properly
            await asyncio.gather(*tasks, return_exceptions=True)
            tasks = [task for task in asyncio.all_tasks() if not task.done()]
            for task in tasks:
                task.cancel()
            print("All asyncio tasks cancelled.")

            # If event loop is still running, stop it
            if loop.is_running():
                loop.stop()
            print("Event loop stopped.")        
            
    def stop(self):
        config["stop"] = True
        with open(config_path, "w") as file:
            json.dump(temp, file, indent=4)

        client.receieve_events["main"].set()
        client.receieve_events["heartbeat"].set()
        client.receieve_events["join_protocol"].set()
        self.heart_stop.set()
        self.rec_stop.set()
        if self.rec_thread:
            self.rec_thread.join(timeout=1)
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1)
    
        for thread in threading.enumerate():
            if thread.name.startswith("asyncio_"):
                print(f"Force stopping {thread.name}...")
                thread.join(timeout=1)  # Try to wait for it to stop
                if thread.is_alive():
                    print(f"Failed to stop {thread.name}, forcibly exiting.")
            
        self.quit()  # Request thread exit
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception as e:
                print(f"error closing socket {e}")
            print("closed sock")
            
        check_threads()
            
class Chat(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat Interface")
        self.main_layout = QVBoxLayout(self)

        # Chat history using QListWidget
        self.chat_list = QListWidget()
        self.main_layout.addWidget(self.chat_list)

          # Input field & send button
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Type a message...")
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)

        self.main_layout.addWidget(self.input_field)
        self.main_layout.addWidget(self.send_button)
    
    def send_message(self):
        message = self.input_field.text().strip()
        user = config["selected_user"] 
        if message and user:
            self.add_message({"user": "you", "message": message})
            msg = client.gen_message("message_user", [user, message], "chat", config["token"])
            print(client.send_to_server(config["client_sock"], msg))
            self.input_field.clear()
        else:
            print("invalid text or no selected user to dm")

    def add_message(self, data):
        client.receieve_events["chat"].set()
        client.receieve_events["chat"].clear()
        username = data["user"]
        message = data["message"]
        item_text = f"{username}: {message}"
        item = QListWidgetItem(item_text)
        self.chat_list.addItem(item)
        self.chat_list.scrollToBottom()

class DropDownMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("drop down menu")
        self.main_layout = QVBoxLayout(self)
        self.online_users = {}
        self.refresh_signal = RemoteSignal()
        self.refresh_signal.signal.connect(self.refresh)
        client.signals["refresh_menu_panel"] = self.refresh_signal.signal
        self.refresh_button = QPushButton("Refresh")
        self.main_layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.request_online_users)

    def request_online_users(self):
        msg = client.gen_message("show_online_users", "refresh_menu_panel", "main", config["token"])
        client.send_to_server(config["client_sock"], msg)
    
    def refresh(self, data):
        users = data["data"]
        for user in users: #adds labels of users
            if user != config["username"] and user not in self.online_users:
                online_user = QPushButton(user)
                self.main_layout.addWidget(online_user)
                online_user.setProperty("user", user)
                online_user.clicked.connect(self.select_user)
                self.online_users[user] = online_user   

        for user in self.online_users: #removes 
            if user not in users and self.online_users[user] != None:
                self.online_users[user].deleteLater()
                self.online_users[user] = None

    def select_user(self):
        button = self.sender()
        config["selected_user"] = button.property("user")
        
class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.rec_stop = threading.Event()
        self.heart_stop = threading.Event()

        self.setWindowTitle("Messaging app")
        self.resize(800, 600)  # Set window size
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.runThread()
       
        self.screen_width = 800
        self.screen_height = 600
     
    def main_menu_layout(self):
        self.clearLayout()

        container = QWidget()
        container_layout = QHBoxLayout()
        container.setLayout(container_layout)

        self.main_chat = Chat(self)
        side_panel = DropDownMenu(self)
        container_layout.addWidget(side_panel, 1)
        container_layout.addWidget(self.main_chat, 2)
        self.main_layout.addWidget(container)

        self.incoming_message_signal = RemoteSignal()
        self.incoming_message_signal.signal.connect(self.main_chat.add_message)
        client.signals["chat"] = self.incoming_message_signal.signal
       
        self.update_ui()

    def login(self):
        if config["login_attempts"] < 3:
            username = self.login_username.text()
            password = self.login_password.text()
            joined = asyncio.run(client.client_joined(config["client_sock"], username, password, config["token"]))
            if joined == 1:
                self.main_menu_layout()
            if not joined:
                config["login_attempts"] += 1

    def login_menu_layout(self):
        self.clearLayout()
        window_size = self.size()  # This returns a QSize object
        width = window_size.width()  # Get the width of the window

        self.main_layout.addItem(QSpacerItem(20, 70, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Username")  # Placeholder text
        self.login_username.setFixedWidth(int(width*0.3))  # Set fixed width to 300 pixels
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")  # Placeholder text
        self.login_password.setFixedWidth(int(width*0.3))  # Set fixed width to 300 pixels
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)  # Hide text


        button = QPushButton("Login")
        button.setStyleSheet("font-size: 15px; color: black;")
        button.clicked.connect(self.login)

        back = QPushButton("Back")
        back.setStyleSheet("font-size: 15px; color: black;")
        back.clicked.connect(self.loginLayout)

        self.main_layout.addWidget(self.login_username, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.login_password, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def register(self):
        if config["register_attempts"] < 5:
            username = self.register_username.text()
            password = self.register_password.text()
            joined = asyncio.run(client.new_user_protocol(config["client_sock"], username, password, config["token"]))
            if joined == 1:
                self.main_menu_layout()
            if not joined:
                config["register_attempts"] += 1

    def register_menu_layout(self):
        self.clearLayout()
        window_size = self.size()  # This returns a QSize object
        width = window_size.width()  # Get the width of the window

        self.main_layout.addItem(QSpacerItem(20, 70, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Username")  # Placeholder text
        self.register_username.setFixedWidth(int(width*0.3))  # Set fixed width to 300 pixels
        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Password")  # Placeholder text
        self.register_password.setFixedWidth(int(width*0.3))  # Set fixed width to 300 pixels
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)  # Hide text

        button = QPushButton("Register")
        button.setStyleSheet("font-size: 15px; color: black;")
        button.clicked.connect(self.register)

        back = QPushButton("Back")
        back.setStyleSheet("font-size: 15px; color: black;")
        back.clicked.connect(self.loginLayout)

        self.main_layout.addWidget(self.register_username, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.register_password, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def connectLayout(self):
        self.clearLayout()
        
        # Spacer on top to push the widget downward
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        label = QLabel("Connecting...")
        label.setStyleSheet("font-size: 15px; color: black;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align text within QLabel
        self.main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.update_ui()

    def loginLayout(self):
        self.clearLayout()
        
        # Spacer on top to push the widget downward
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        button = QPushButton("Login")
        button.setStyleSheet("font-size: 15px; color: black;")
        button.clicked.connect(self.login_menu_layout)
        #button.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align text within QLabel
        self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        button = QPushButton("Register")
        button.setStyleSheet("font-size: 15px; color: black;")
        button.clicked.connect(self.register_menu_layout)
       # button.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align text within QLabel
        self.main_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        self.update_ui()
    
    def closeEvent(self, event):
        self.appThread.stop()
        #sys.exit(0)  # Force terminate if needed
    
    def clearLayout(self):
        """Removes all widgets from the layout."""
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
    
    def update_ui(self):
        """Forces the UI to refresh after layout changes."""
        self.update()
        self.repaint()
    
    def runThread(self):
        self.appThread = Client_thread()
        self.appThread.rec_stop = self.rec_stop
        self.appThread.heart_stop = self.heart_stop
        self.appThread.login_signal.connect(self.loginLayout)
        self.appThread.start()
