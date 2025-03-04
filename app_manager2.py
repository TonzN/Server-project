from loads import *
from client.loads import *
import client.client_manager2 as client
from client.thread_manager import * 
from  client.client_utils import *

HOST = "localhost"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

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
            
            try:
                self.run_client(self.client_sock, self.login_signal)

            except Exception as e:
                print(f"Error {e}")

            finally:
                print("closed thread socket")
                return

    def run_client(self, client_sock, login_signal):
        config["client_sock"] = client_sock
        self.rec_thread = threading.Thread(target=client.receive_thread, args=(client_sock, self.rec_stop), daemon=True)
        self.rec_thread.start()
    
        try: 
            token = client.receieve_queue["join_protocol"].get(timeout=1)
            
            if token:
                login_signal.emit()
                config["token"] = token
                self.heartbeat_thread = threading.Thread(target=client.heartbeat, args=(client_sock, self.heart_stop, config["token"]), daemon=True)
                self.heartbeat_thread.start()
              
                client.run_client(client_sock, self.heart_stop)
            else:
                print("token invalid")   

        except Exception as e:
            print(f"heh {e}")
            return
             
    def stop(self):
        config["stop"] = True
        with open(config_path, "w") as file:
            json.dump(temp, file, indent=4)

        self.heart_stop.set()
        self.rec_stop.set()
        if self.rec_thread:
            self.rec_thread.join(timeout=1)
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=3.6)
            
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception as e:
                print(f"error closing socket {e}")
            print("closed sock")
            
        check_threads()
        os.remove(config_path)
        self.quit()  # Request thread exit
        os._exit(0)
            
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
        if config["send_type"] == "user":
            user = config["selected_user"] 
            if message and user:
                self.add_message({"user": "you", "message": message})
                msg = client.gen_message("message_user", [user, message], "chat", config["token"])
                client.send_to_server(config["client_sock"], msg)
                self.input_field.clear()
            else:
                print("invalid text or no selected user to dm")
        elif config["send_type"] == "group":
            if config["selected_group"] != False:
                if config["selected_group"] == "global":
                    self.add_message({"user": "[global] you", "message": message})
                    msg = client.gen_message("message_group", [config["selected_group"], message], "chat", config["token"])
                    client.send_to_server(config["client_sock"], msg)
                    self.input_field.clear()

    def add_message(self, data):
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
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.online_users = {}
        self.refresh_signal = RemoteSignal()
        self.refresh_signal.signal.connect(self.refresh)
        client.signals["refresh_menu_panel"] = self.refresh_signal.signal
        self.refresh_button = QPushButton("Refresh")
        # self.main_layout.addWidget(self.refresh_button)
        create_group = QPushButton("Global chat")
        create_group.clicked.connect(self.select_group)
        self.main_layout.addWidget(create_group)
        users_label = QLabel("Users")
        self.main_layout.addWidget(users_label)

        self.refresh_button.clicked.connect(request_online_users)
        client.heartbeat_functions["req_online_users"] = request_online_users

    def select_group(self):
        config["send_type"] = "group"
        config["selected_group"] = "global"

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
        config["send_type"] = "user"
        config["selected_group"] == False
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
            joined = client.client_joined(config["client_sock"], username, password, config["token"])
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
            joined = client.new_user_protocol(config["client_sock"], username, password, config["token"])
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
