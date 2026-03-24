import socket, threading
from datetime import datetime

def get_time():
    return datetime.now().strftime("%H:%M:%S")

# 1. Ввод данных
my_name = input("Введите ваше имя: ")
my_ip = input("Введите ваш IP (настоящий адрес Wi-Fi): ")
my_tcp_port = int(input("Введите ваш TCP порт: "))

UDP_PORT = 2509

print(f"\n[{get_time()}] ~~~~~~~ Привет, {my_name}! Твой IP: {my_ip}, TCP-порт: {my_tcp_port} ~~~~~~~~")

neighbrs = {}

# 2. Настройка и отправка UDP через broadcast
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) # Магия macOS для разделения порта

udp_sock.bind(('', UDP_PORT)) # Слушаем весь эфир

my_info = f"{my_name}:{my_tcp_port}"
info_encode = my_info.encode('utf-8')
message = bytes([3, len(info_encode)]) + info_encode

# Отправляем на глобальный широковещательный адрес
ip_parts = my_ip.split('.')
broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"

udp_sock.sendto(message, (broadcast_ip, UDP_PORT))
print(f"[{get_time()}] UDP пакет для поиска друзей отправлен\n")

# 3. Функции обработки
def listen_udp():
    while True:
        try:
            data, addr = udp_sock.recvfrom(1024)
            sender_ip = addr[0]

            if data[0] == 3:
                name_length = data[1]
                sender_name = data[2 : 2 + name_length].decode('utf-8')
                friend_name, friend_tcp_port_str = sender_name.split(":")
                friend_tcp_port = int(friend_tcp_port_str)

                # Игнорируем СВОИ ЖЕ эхо-пакеты (по совпадению нашего TCP-порта)
                if friend_tcp_port == my_tcp_port:
                    continue

                if sender_ip not in neighbrs or neighbrs[sender_ip][1] != friend_tcp_port:
                    neighbrs[sender_ip] = (friend_name, friend_tcp_port)
                    # Страховка для локального тестирования
                    neighbrs['127.0.0.1'] = (friend_name, friend_tcp_port)
                    print(f"[{get_time()}] [+] К чату присоединился: {friend_name} ({sender_ip}:{friend_tcp_port})")
                    
                    # Отправляем ответ, чтобы друг тоже нас записал
                    udp_sock.sendto(message, (sender_ip, UDP_PORT))
        except Exception:
            pass

def helper_client(conn, addr):
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            text = data.decode('utf-8')
            friend_data = neighbrs.get(addr[0], ("Неизвестный", 0)) 
            print(f"[{get_time()}] [{friend_data[0]}] : {text}")
        except Exception:
            break
    conn.close()

def listen_tcp():
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind((my_ip, my_tcp_port))
    tcp_server.listen(5)
    while True:
        client_sock, client_addr = tcp_server.accept()
        threading.Thread(target=helper_client, args=(client_sock, client_addr), daemon=True).start()

# 4. Запуск фоновых процессов
threading.Thread(target=listen_udp, daemon=True).start()
threading.Thread(target=listen_tcp, daemon=True).start()

# 5. Отправка сообщений
while True:
    text = input()
    if not text:
        continue
        
    if not neighbrs:
        print(f"[{get_time()}] Системное сообщение: Отправлять некому, список узлов пуст!")
        continue
  
    for find_ip in list(neighbrs.keys()):
        if find_ip == '127.0.0.1' and my_ip != '127.0.0.1':
            continue
        try:
            friend_tcp_port = neighbrs[find_ip][1]
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_sock.connect((find_ip, friend_tcp_port))
            send_sock.send(text.encode('utf-8'))
            send_sock.shutdown(socket.SHUT_RDWR)
            send_sock.close()
        except Exception as e:
            print(f"[{get_time()}] Не удалось отправить на {find_ip}: {e}")