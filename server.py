import socket
import asyncio
import aioconsole

class ChatClient:
    def __init__(self, username, address, port,status):
        self.username = username
        self.address = address
        self.port = port
        self.status = status
        self.chatRoomJoining = True
        
class ChatRoom:
    def __init__(self,roomName, maxMember, client):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.address = '127.0.0.1'
        self.port = 9002
        self.roomName = roomName
        self.maxMember = maxMember
        self.participants = {(client.address) + str(client.port): client}
        self.hostMap = {(client.address) + str(client.port): client}

    async def sendMessage(self):
        while True:
            message = await aioconsole.ainput()
            loop = asyncio.get_event_loop()

            for client in self.participants.values():
                await loop.sock_sendto(self.sock, message.encode("utf-8"), (client.address, client.port))
            
            print ("\033[A                             \033[A")
            print("\nServer: {}".format(message))
            await asyncio.sleep(0.1)

    async def receveMessage(self):
        while True:
            loop = asyncio.get_event_loop()
            data, address = await loop.sock_recvfrom(self.sock, 4096)
            userNameOfData = self.participants[address[0] + str(address[1])].username

            if data:
                print("\n{}: {}".format(userNameOfData, data.decode("utf-8")))     
            await asyncio.sleep(0.1)

    async def main(self):
        try: 
             async with asyncio.TaskGroup() as tg:
                task1 = tg.create_task(self.receveMessage())
                task2 = tg.create_task(self.sendMessage())
    
        except Exception as e:
            print("Error: " + str(e))
            self.sock.close()
        
    def startChat(self):
        print('\nStart the new chat room "{}"'.format(self.roomName))
        
        self.sock.bind((self.address, self.port))

        try:
            asyncio.run(self.main())
            # asyncio.run(self.sendMessage())
            # self.sock.settimeout(2)
        
        except TimeoutError as e:
            print(e)
            self.sock.close()
        

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

                connection.sendall(user_port.to_bytes(2, "big"))
                chatClient = self.makeChatClient(username, user_address,user_port,service_type)

                # service_tyepが1の場合は新しいチャットルームを作成して、開始。2の場合は既存のチャットルームに参加。
                if service_type == "1":
                    newChatroom = self.makeChatroom(chat_roomName, maxMember, chatClient)
                    self.chatRooms[newChatroom.roomName] = newChatroom
                    newChatroom.startChat()
                else:
                    # service_typeが2の場合は既存のチャットルームがあるかどうか、人数が上限に達していないかどうか確認して、問題なかったら参加。
                    if self.findChatRoom(chat_roomName) is False:
                        message = "{} is does not exist".format(chat_roomName)
                        self.sock.send(message)
                    elif self.checkChatRoomCapacity(chat_roomName) is False:
                        message = "{} is full".format(chat_roomName)
                    else:
                        self.addClientToChatRoom(chatClient, chat_roomName)
                        
                    
            except Exception as e:
                print('Error: ' + str(e))
                
        
    def makeChatClient(self ,username, address, port, service_type):
        status = "host" if service_type == "1" else "participant"
        return ChatClient(username, address, port, status)
    
    def makeChatroom(self, roomName, maxMember, client):
        return ChatRoom(roomName, maxMember, client)
    
    def findChatRoom(self,roomName):
        return self.chatRooms[roomName] != None
    
    def checkChatRoomCapacity(self,roomName):
        chatRoom = self.chatRooms[roomName]
        return len(chatRoom.participants) < chatRoom.maxMember
    
    def addClientToChatRoom(self, client, roomName):
        chatRoom = self.chatRooms[roomName]
        chatRoom.participants[client.address + str(client.port)] = client
    
class Main:
    server = Server()
    server.accept()
    
if __name__ == "__main__":
    Main()