import cv2
import mediapipe as mp
import pyautogui
import time
import keyboard

# ---------------------- Настройки пользователя ----------------------
CAMERA_INDEX = 0  # Индекс видеоустройства (0 = первая камера)
FRAME_SKIP = 1  # Обрабатывать каждый n-й кадр
CAM_RESOLUTION = (1920, 1080)  # Разрешение видеокадра (Ш×В)
MODEL_COMPLEXITY = 0  # Сложность модели MediaPipe Hands (0 = лёгкая)
DETECTION_CONFIDENCE = 0.2  # Минимальная уверенность детекции
TRACKING_CONFIDENCE = 0.2  # Минимальная уверенность трекинга
CLICK_THRESHOLD = 0.05  # Порог «щипка» для клика
TOGGLE_KEY = 'f9'  # Горячая клавиша для вкл/выкл трекинга

# -------------------- Глобальное состояние приложения -----------------------
tracking_enabled = True  # Флаг обработки кадров
screen_w, screen_h = pyautogui.size()  # Размер экрана для перемещения курсора

# ------------------- Инициализация MediaPipe Hands -------------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils  # Для отрисовки ключевых точек
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=MODEL_COMPLEXITY,
    min_detection_confidence=DETECTION_CONFIDENCE,
    min_tracking_confidence=TRACKING_CONFIDENCE,
)


# ------------------- Функция переключения трекинга ---------------------
def toggle_tracking():
    global tracking_enabled
    tracking_enabled = not tracking_enabled
    print(f"Трекинг {'включён' if tracking_enabled else 'выключен'}")


keyboard.add_hotkey(TOGGLE_KEY, toggle_tracking)


# ---------------------- Основная функция ------------------------
def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_RESOLUTION[1])

    frame_idx = 0
    last_click_time = 0
    click_cooldown = 0.3

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            frame_idx += 1
            if frame_idx % FRAME_SKIP != 0 or not tracking_enabled:
                cv2.imshow("Gesture Control", frame)
                if cv2.waitKey(1) & 0xFF == 27:  # Выход по ESC
                    break
                continue

            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Отрисовка ключевых точек и соединений
                    mp_drawing.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0)),  # Цвет точек (BGR)
                        mp_drawing.DrawingSpec(color=(255, 0, 0))  # Цвет линий
                    )

                    # Получаем координаты кончика указательного пальца (landmark 8)
                    lm = hand_landmarks.landmark
                    ix, iy = lm[8].x, lm[8].y
                    print(f"Кончик указательного пальца: X={ix:.2f}, Y={iy:.2f}")

                    # Преобразуем координаты и перемещаем курсор
                    screen_x = screen_w - (ix * screen_w)
                    screen_y = iy * screen_h
                    if tracking_enabled:  # Добавлена проверка флага
                        pyautogui.moveTo(screen_x, screen_y, duration=0)

                    # Проверка жеста "щипок" (клик)
                    thumb = lm[4]
                    index_tip = lm[8]
                    pinch_dist = ((thumb.x - index_tip.x) ** 2 + (thumb.y - index_tip.y) ** 2) ** 0.5
                    now = time.time()
                    if pinch_dist < CLICK_THRESHOLD and (now - last_click_time) > click_cooldown:
                        if tracking_enabled:  # Кликаем только при активном трекинге
                            pyautogui.click()
                            last_click_time = now
                            print("Левый клик!")

            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == 27:  # Выход по ESC
                break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hands.close()
        print("Завершено")


if __name__ == '__main__':
    print(f"Нажмите {TOGGLE_KEY.upper()} для вкл/выкл трекинга")
    main()