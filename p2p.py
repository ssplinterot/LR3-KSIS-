import socket, threading, time
from datetime import datetime
# функция получения красивого времени
def get_time():
    return datetime.now().strftime("%H:%M:%S")

# 1. Ввод данных
my_name = input("Введите ваше имя: ")
my_ip = input("Введите ваш IP (настоящий адрес Wi-Fi): ")
my_tcp_port = int(input("Введите ваш TCP порт: "))

UDP_PORT = my_tcp_port # UDP-порт делаем таким же, как TCP, чтобы они были уникальными для каждого окна при тесте на одном ПК

print(f"\n[{get_time()}] ~~~~~~~ Привет, {my_name} Твой IP: {my_ip}, Порт: {my_tcp_port} ~~~~~~~~")

neighbrs = {} # создаём словарь(будут записываться те кто онлайн) 

# 2. Настройка UDP (Broadcast)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) # создание udp сокета
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) # SO_BROADCAST разрешает отправлять пакеты всем сразу
udp_sock.bind((my_ip, UDP_PORT)) 

my_info = f"{my_name}:{my_tcp_port}"
message = bytes([3, len(my_info.encode('utf-8'))]) + my_info.encode('utf-8') # сообщение наичнаеться с байта 3, затем идет длина текста, а затем сам текст "Имя:Порт"

# превращаем наш ip в широковещательный адрес нашей сети
ip_parts = my_ip.split('.') # разбиваем IP на 4 кусочка по точкам
broadcast_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255" if len(ip_parts) == 4 else '255.255.255.255'

udp_sock.sendto(message, (broadcast_ip, UDP_PORT))
print(f"[{get_time()}] UDP пакет для поиска друзей отправлен\n")

def udp_broadcaster(): # Постоянно (каждые 3 секунды) кричит в сеть, что мы онлайн
    while True:
        try:
            for port in range(2500, 2520): # Прозваниваем порты с запасом
                if port != my_tcp_port: 
                    udp_sock.sendto(message, (my_ip, port))
        except Exception:
            pass
        time.sleep(3) # Ждем 3 секунды перед следующим криком

# 3. Функции обработки
def listen_udp(): # слушает эфир и ловит приветствия от других
    while True:
        try:
            data, addr = udp_sock.recvfrom(1024) # . recvfrom возвращает сами данные (data) и адрес отправителя (addr)
            sender_ip = addr[0] # вытаскиваем IP-адрес отправителя

            if data[0] == 3:
                name_length = data[1]
                # расшифровываем полезную нагрузку пакета
                sender_name = data[2 : 2 + name_length].decode('utf-8')
                friend_name, friend_tcp_port_str = sender_name.split(":")
                friend_tcp_port = int(friend_tcp_port_str)

                # Игнорируем себя
                if friend_tcp_port == my_tcp_port:
                    continue
                # Создаем уникальный ключ "IP:Порт"
                peer_key = f"{sender_ip}:{friend_tcp_port}"

                if peer_key not in neighbrs:
                    neighbrs[peer_key] = (friend_name, friend_tcp_port, sender_ip)
                    print(f"\n[{get_time()}] [+] К чату присоединился: {friend_name} (Порт: {friend_tcp_port})")
                    print("Введите ваше сообщение: ", end="", flush=True)
             
        except Exception:
            pass

def helper_client(conn, addr):# обрабатывает  входящее сообщение от  друга
    try:
        data = conn.recv(1024) # принимаем до 1024 байт текста от друга
        if data:
            raw_text = data.decode('utf-8')
            
            # Ищем разделитель. Если он есть, разбиваем на имя и текст
            if "|" in raw_text: # если есть - режем на Имя и Текст.
                friend_name, text = raw_text.split("|", 1)
            else:
                friend_name = "Неизвестный"
                text = raw_text

            print(f"\n[{get_time()}] [{friend_name}] : {text}", flush=True)
            print("Введите ваше сообщение: ", end="", flush=True)
    except Exception:
        pass
    finally:
        conn.close()

def listen_tcp(): # TCP-сервер сидит на нашем порту и принимает звонки от других
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # создание tcp сокетов
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Чтобы порт не зависал. SO_REUSEADDR разрешает сразу занять порт после перезапуска скрипта, даже если он висит в TIME_WAIT
    tcp_server.bind((my_ip, my_tcp_port))
    tcp_server.listen(5) # очередь
    while True:
        client_sock, client_addr = tcp_server.accept() # accept() замирает и ждет
        threading.Thread(target=helper_client, args=(client_sock, client_addr), daemon=True).start()
        # создаём новый поток для обработки этого сообщения

# 4. Запуск процессов
threading.Thread(target=listen_udp, daemon=True).start() # daemon=True означает, что эти потоки умрут сами, как только мы закроем главную программу
threading.Thread(target=listen_tcp, daemon=True).start()
threading.Thread(target=udp_broadcaster, daemon=True).start() # поток, который обновляеться каждые 3 секунды

# 5. Главный цикл
while True:
    text = input("Введите ваше сообщение: ")
    if not text:
        continue
        
    if not neighbrs:
        print(f"[{get_time()}] Отправлять некому, список узлов пуст! Ждем подключения...")
        continue
  
    # Достаем данные из обновленного словаря
    for peer_key, info in list(neighbrs.items()):
        try:
            friend_tcp_port = info[1] # Достаем порт друга
            find_ip = info[2] # Достаем IP друга
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_sock.connect((find_ip, friend_tcp_port))  #тут происходит тройное рукопожатие
            full_msg = f"{my_name}|{text}"
            send_sock.sendall(full_msg.encode('utf-8')) # отправляем сообщение целиком (sendall использует скользящее TCP-окно)
            send_sock.close() # отправка fin пакета
        except Exception:
            pass