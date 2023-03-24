import socket

class ChatClient:
    def __init__(self, username, address, port,status):
        self.username = username
        self.address = address
        self.port = port
        self.status = status
        self.chatRoomJoining = None
        
class ChatRoom:
    def __init__(self,roomName, maxMember, client):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = '127.0.0.1'
        self.port = 9002
        self.roomName = roomName
        self.maxMember = maxMember
        self.participants = 1
        self.hostMap = {"hostName": client.username, "host": client}
        
    def startChat(self,client):
        print('\nStart the new chat room "{}"'.format(self.roomName))
        
        self.sock.bind((self.address, self.port))
        
        while True:
            data, address = self.sock.recvfrom(4096)
            
            
            print("{}: {}".format(address, data.decode("utf-8")))


            message = "bot: i am a bot machine.".encode("utf-8")
            self.sock.sendto(message, (address[0],address[1]))
            
        
class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '127.0.0.1'
        self.port = 9005
        self.chatRooms = {}
     
    # clientとTCP接続   
    def accept(self):
        print("Starting up on {} port {}".format(self.address,self.port))

        # 切断した後すぐに再利用するためにオプションを設定
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        self.sock.listen(1)
        
        while True:
            connection, client_address = self.sock.accept()
            user_address = client_address[0]
            user_port = client_address[1]
            
            try:
                print('connection from', client_address)
                header = connection.recv(8)
                
                username_length = int.from_bytes(header[:2],"big")
                user_selected_service_length = int.from_bytes(header[3:4],"big")
                chat_roomName_lengh = int.from_bytes(header[5:6], "big")
                maxMember_length = int.from_bytes(header[7:8],"big")
                
                username = connection.recv(username_length).decode("utf-8")
                service_type = connection.recv(user_selected_service_length).decode("utf-8")
                stringOfService = "make a new room" if service_type == "1" else "join in a room"
                
                chat_roomName = connection.recv(chat_roomName_lengh).decode("utf-8")
                maxMember = connection.recv(maxMember_length).decode("utf-8")
                
                print(header)
                print(len(header))
                
                print("Username: {}".format(username))
                print("Service Type: {}".format(stringOfService))
                print("User adress: {}".format(client_address))
                
                
                chatClient = Server.makeChatClient(username, client_address[0],client_address[1],service_type)

                # service_tyepが1の場合は新しいチャットルームを作成して、開始。2の場合は既存のチャットルームに参加。
                if service_type == "1":
                    newChatroom = Server.makeChatroom(chat_roomName, maxMember, chatClient)
                    self.chatRooms[chatClient.address + str(chatClient.port)] = newChatroom
                    newChatroom.startChat(chatClient)
                else:
                    print("join chat room")
            
            except Exception as e:
                print('Error: ' + str(e))
                
        
    def makeChatClient(username, address, port, service_type):
        status = "host" if service_type == "1" else "participant"
        return ChatClient(username, address, port, status)
    
    def makeChatroom(roomName, maxMember, client):
        return ChatRoom(roomName, maxMember, client)
    
class Main:
    server = Server()
    server.accept()
    
if __name__ == "__main__":
    Main()