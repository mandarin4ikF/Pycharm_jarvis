import cv2
import mediapipe as mp
import pyautogui
import time
import keyboard

# ╔═══════════════════════════════════════╗
# ║            ПЕРЕМЕННЫЕ НАСТРОЕК        ║
# ╚═══════════════════════════════════════╝

CAMERA_INDEX = 0               # Индекс камеры (0 — обычно встроенная веб-камера)
FRAME_SKIP = 1                 # Пропуск кадров: 1 — обрабатывать каждый кадр
CAM_RESOLUTION = (1280, 720)   # Разрешение видеопотока с камеры (ширина, высота)
MODEL_COMPLEXITY = 0           # Сложность модели MediaPipe (0 — базовая, 1 — средняя, 2 — высокая)
DETECTION_CONFIDENCE = 0.5     # Минимальная уверенность обнаружения руки (0-1)
TRACKING_CONFIDENCE = 0.5      # Минимальная уверенность отслеживания (0-1)
CLICK_THRESHOLD = 0.04         # Порог расстояния для распознавания жеста "щипок" (клик)
TOGGLE_KEY = 'f9'              # Клавиша для включения/выключения трекинга
SMOOTHING = 0.65               # Коэффициент сглаживания движения курсора (0 — нет сглаживания, 1 — максимальное)
MOVE_THRESHOLD = 8             # Минимальное смещение курсора в пикселях, чтобы произвести движение (игнорирует мелкие дрожания)

# ╔═══════════════════════════════════════╗
# ║          СОСТОЯНИЕ ПРОГРАММЫ          ║
# ╚═══════════════════════════════════════╝

tracking_enabled = True        # Флаг, включен ли трекинг
screen_w, screen_h = pyautogui.size()  # Получаем размеры экрана пользователя
prev_x, prev_y = screen_w // 2, screen_h // 2  # Начальная позиция курсора — центр экрана

# ╔═══════════════════════════════════════╗
# ║         ИНИЦИАЛИЗАЦИЯ MEDIAPIPE       ║
# ╚═══════════════════════════════════════╝

mp_hands = mp.solutions.hands               # Импортируем модуль распознавания рук
mp_drawing = mp.solutions.drawing_utils    # Утилиты для рисования точек и линий на изображении

hands = mp_hands.Hands(
    static_image_mode=False,                 # Режим: False — для видео (не одиночного изображения)
    max_num_hands=1,                         # Отслеживаем только одну руку
    model_complexity=MODEL_COMPLEXITY,      # Сложность модели (от нее зависит качество и скорость)
    min_detection_confidence=DETECTION_CONFIDENCE,  # Порог уверенности для обнаружения руки
    min_tracking_confidence=TRACKING_CONFIDENCE,    # Порог уверенности для отслеживания руки
)

# ╔═══════════════════════════════════════╗
# ║         ФУНКЦИЯ ПЕРЕКЛЮЧЕНИЯ          ║
# ╚═══════════════════════════════════════╝

def toggle_tracking():
    global tracking_enabled
    tracking_enabled = not tracking_enabled
    print(f"[INFO] Трекинг {'включён' if tracking_enabled else 'выключен'}")

# Назначаем горячую клавишу для включения/выключения трекинга
keyboard.add_hotkey(TOGGLE_KEY, toggle_tracking)

# ╔═══════════════════════════════════════╗
# ║   О С Н О В Н А Я  Ф У Н К Ц И Я      ║
# ╚═══════════════════════════════════════╝

def main():
    global prev_x, prev_y

    # Запускаем видеопоток с камеры
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_RESOLUTION[0])   # Устанавливаем ширину
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_RESOLUTION[1])  # Устанавливаем высоту

    frame_idx = 0          # Счётчик кадров
    last_click_time = 0    # Время последнего клика (для антидребезга)
    click_cooldown = 0.4   # Минимальное время между кликами в секундах

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue  # Если кадр не получен, переходим к следующему

            frame = cv2.flip(frame, 2)  # Отражаем кадр по горизонтали для "зеркального" эффекта
            frame_idx += 1

            # Пропуск кадров или если трекинг выключен — просто показываем видео и ждём
            if frame_idx % FRAME_SKIP != 0 or not tracking_enabled:
                cv2.imshow("Gesture Control", frame)
                if cv2.waitKey(1) & 0xFF == 27:  # ESC для выхода
                    break
                continue

            # Конвертируем изображение в RGB для MediaPipe
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Обработка кадра моделью распознавания рук
            results = hands.process(img_rgb)

            # Если рука обнаружена
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Рисуем скелет руки на кадре
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2))

                    lm = hand_landmarks.landmark

                    # Выбираем опорную точку — средняя фаланга среднего пальца (точка 12)
                    ref_x, ref_y = lm[12].x, lm[12].y

                    # Переводим нормализованные координаты в экранные с инверсией по X для удобства управления
                    target_x = screen_w - (ref_x * screen_w)
                    target_y = ref_y * screen_h

                    # Сглаживание движения курсора
                    smooth_x = int(prev_x + (target_x - prev_x) * SMOOTHING)
                    smooth_y = int(prev_y + (target_y - prev_y) * SMOOTHING)

                    dx = abs(smooth_x - prev_x)
                    dy = abs(smooth_y - prev_y)

                    # Двигаем мышь, если сдвиг превышает порог и трекинг включён
                    if tracking_enabled and (dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD):
                        pyautogui.moveTo(smooth_x, smooth_y, duration=0)
                        prev_x, prev_y = smooth_x, smooth_y

                    # Жест "щипок": расстояние между большим и указательным пальцем
                    thumb = lm[4]
                    index_tip = lm[8]
                    pinch_dist = ((thumb.x - index_tip.x) ** 2 + (thumb.y - index_tip.y) ** 2) ** 0.5

                    now = time.time()
                    # Если пальцы достаточно близко и прошло достаточно времени с прошлого клика — делаем клик
                    if pinch_dist < CLICK_THRESHOLD and (now - last_click_time) > click_cooldown:
                        pyautogui.click()
                        last_click_time = now
                        print("[ACTION] Левый клик")

            # Показываем кадр с визуализацией
            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC — выход
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("[EXIT] Программа завершена")


if __name__ == '__main__':
    print(f"[INFO] Нажмите {TOGGLE_KEY.upper()} для включения/отключения трекинга")
    main()
