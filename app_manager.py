from loads import *
from client.loads import *
import client.client_manager as client



HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 12345  # The port used by the server

async def run_client(client_sock, login_signal):
    config["client_sock"] = client_sock

    rec_stop = threading.Event()
    rec_thread = threading.Thread(target=client.receive_thread, args=(client_sock, rec_stop), daemon=True)
    rec_thread.start()
    await asyncio.wait_for(asyncio.to_thread(client.receieve_events["join_protocol"].wait), timeout=5)
    token = await client.receieve_queue["join_protocol"].get()
    client.receieve_events["join_protocol"].clear()
    time.sleep(0.5) #artificial delay
    
    if token:
        login_signal.emit()
        config["token"] = token
        client.run_client(client_sock)
    else:
        return 

class Client_thread(QThread):
    login_signal = pyqtSignal()
    
    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
            try:
                client_sock.connect((HOST, PORT))
                print(f"Client connected.\n")
            except socket.timeout:
                print("Client timeout: attempted connecting for too long")
                return
            except Exception as e:
                print(f"Client did not connect: {e}\n")
                return  
            
            asyncio.run(run_client(client_sock, self.login_signal))
            
           

class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Messaging app")
        self.resize(800, 600)  # Set window size
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.runThread()
       
        self.screen_width = 800
        self.screen_height = 600
     
    def main_menu_layout(self):
        self.clearLayout()
        
        # Spacer on top to push the widget downward
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        label = QLabel("Menu")
        label.setStyleSheet("font-size: 15px; color: black;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Align text within QLabel
        self.main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
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
        self.appThread.login_signal.connect(self.loginLayout)
        self.appThread.start()
   