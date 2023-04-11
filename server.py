import socket
import asyncio
import _thread
import random
import re

class ChatClient:
    def __init__(self, username, address, port,status):
        self.username = username
        self.address = address
        self.port = port
        self.status = status
        
class ChatRoom:
    def __init__(self,port, roomName, maxMember, client):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.address = '127.0.0.1'
        self.port = port
        self.roomName = roomName
        self.maxMember = maxMember
        self.participants = {(client.address) + str(client.port): client}
        self.hostMap = {(client.address) + str(client.port): client}

    def existParticipants(self):
        return len(self.participants) >= 1

    async def announceFromServer(self, message):
        loop = asyncio.get_event_loop()

        for client in self.participants.values():
            await loop.sock_sendto(self.sock, message.encode("utf-8"), (client.address, client.port))
        
        await asyncio.sleep(0.1)
    
    async def deleteParticipant(self, address):
        key = address[0] + str(address[1])
        target = self.participants[key]
        del self.participants[key]
        
        if self.existParticipants() == True:
            announce = "Server: {} left the room.".format(target.username)
            await self.announceFromServer(announce)
        else:
            print("{} has been closed.".format(self.roomName))
            self.sock.close()

    def extractMessage(self, data):
        data = data.decode("utf-8")

        if data == "{}:join".format(self.roomName):
            return "join"
        else:
            extractMessagePattern = self.roomName + ":" + r'[0-9]*' + ":"
            return re.split(extractMessagePattern, data)[1]

    async def sendMessage(self,message,sender):
        loop = asyncio.get_event_loop()
        
        for client in self.participants.values():
            if sender != client:
                await loop.sock_sendto(self.sock, message.encode("utf-8"), (client.address, client.port))
        
        await asyncio.sleep(0.1)

    async def receveData(self):
        while self.existParticipants():
            loop = asyncio.get_event_loop()
            data, address = await loop.sock_recvfrom(self.sock, 4096)
            sender = self.participants[address[0] + str(address[1])]

            if data:
                message = self.extractMessage(data)
                if message == "real-Bye-Bye":
                    await self.deleteParticipant(address)
                else:    
                    messageToSend = "{}: {}".format(sender.username, message)
                    print(messageToSend)   
                    await self.sendMessage(messageToSend,sender)  
          
            await asyncio.sleep(0.1)


    def startChat(self):
        print('\nStart the new chat room "{}"'.format(self.roomName))
        print("port is {}".format(self.port))
        self.sock.bind((self.address, self.port))

        try:
            asyncio.run(self.receveData())

        except Exception as e:
            print("Error: " + str(e))
            self.sock.close()
        
        finally:
            self.sock.close()

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '127.0.0.1'
        self.port = 9005
        self.chatRooms = {} # key roomname: Chatroom chatroom
     
    # clientとTCP接続   
    def accept(self):
        print("Starting up on {} port {}".format(self.address,self.port))

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.address, self.port))
        self.sock.listen(128)
        
        while True:
            connection, client_address = self.sock.accept()
            _thread.start_new_thread(self.getUserData,(connection, client_address))
            
    def promptChatRoomName(self,connection, sizeOfDataReceivePerOnce, service_type):
        while True:
            chat_roomName_lengh = int.from_bytes(connection.recv(sizeOfDataReceivePerOnce), "big")
            chat_roomName = connection.recv(chat_roomName_lengh).decode("utf-8")
            
            if service_type == "2":
                if chat_roomName not in self.chatRooms or chat_roomName in self.chatRooms and self.checkChatRoomCapacity(chat_roomName) is False:
                    connection.sendall((0).to_bytes(2, "big"))
                    
                else:
                    connection.sendall((1).to_bytes(2, "big"))
                    return chat_roomName
                
            elif service_type == "1" and chat_roomName in self.chatRooms:
                connection.sendall((0).to_bytes(2, "big"))
                
            else:
                connection.sendall((1).to_bytes(2, "big"))
                return chat_roomName
                
    def getUserData(self, connection, client_address):
        user_address = client_address[0]
        user_port = client_address[1]
        
        try:
            print('connection from', client_address)
            sizeOfDataReceivePerOnce  = 2
            
            username_length = int.from_bytes(connection.recv(sizeOfDataReceivePerOnce), "big")
            username = connection.recv(username_length).decode("utf-8")
            print("Username: {}".format(username))

            user_selected_service_length = int.from_bytes(connection.recv(sizeOfDataReceivePerOnce),"big")
            service_type = connection.recv(user_selected_service_length).decode("utf-8")
            stringOfService = "make a new room" if service_type == "1" else "join in a room"
            print("Service Type: {}".format(stringOfService))   
            
            chat_roomName = self.promptChatRoomName(connection,sizeOfDataReceivePerOnce,service_type)
            print("Chat room name is {}".format(chat_roomName))
            
            maxMember_length = int.from_bytes(connection.recv(sizeOfDataReceivePerOnce),"big")
            maxMember = connection.recv(maxMember_length).decode("utf-8")
            
            print("User adress: {}".format(client_address))

            connection.sendall(user_port.to_bytes(2, "big"))
            chatClient = self.makeChatClient(username, user_address,user_port,service_type)

            # service_tyepが1の場合は新しいチャットルームを作成。
            if service_type == "1":
                # 2000以上のポート番号をランダムで割り当てる
                chatroom_port = random.randint(2000, 65500)
                connection.sendall(chatroom_port.to_bytes(2, "big"))
                
                newChatroom = self.makeChatroom(chatroom_port,chat_roomName, maxMember, chatClient)
                self.chatRooms[newChatroom.roomName] = newChatroom
                newChatroom.startChat()
                
            else:
                # service_typeが2の場合はチャットルームに参加
                chatroom_port = self.chatRooms[chat_roomName].port
                connection.sendall(chatroom_port.to_bytes(2, "big"))
                self.addClientToChatRoom(chatClient, chat_roomName)
                
        except Exception as e:
            print('Error: ' + str(e))
                
        
    def makeChatClient(self ,username, address, port, service_type):
        status = "host" if service_type == "1" else "participant"
        return ChatClient(username, address, port, status)
    
    def makeChatroom(self,chatroom_port,roomName, maxMember, client):
        return ChatRoom(chatroom_port, roomName, maxMember, client)
    
    def checkChatRoomCapacity(self,roomName):
        chatRoom = self.chatRooms[roomName]
        return len(chatRoom.participants) < int(chatRoom.maxMember)
    
    def addClientToChatRoom(self, client, roomName):
        chatRoom = self.chatRooms[roomName]
        chatRoom.participants[client.address + str(client.port)] = client
    
class Main:
    server = Server()
    server.accept()
    
if __name__ == "__main__":
    Main()