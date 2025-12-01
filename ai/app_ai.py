import os
import threading
from tkinter import *
from tkinter import filedialog, messagebox
from PIL import ImageTk
from tools.generator import generate_image
from tools.image_tools import cut_center_transparent
from tools.csv_loader import load_params

pipe = None
current_loaded_path = None

save_folder = ""
overlay_path = ""
generating = False
cancel_generation = False


AVAILABLE_MODELS = {
    "RealVisXL (SDXL)": ("sdxl", r"models\realvisxl"),
    "SDXL Base 1.0": ("sdxl", r"models\stable-diffusion-xl-base-1.0")
}

selected_model = None
    

def select_folder():
    global save_folder
    folder = filedialog.askdirectory()
    if folder:
        save_folder = folder
        folder_label.config(text=save_folder)

def select_overlay():
    global overlay_path
    path = filedialog.askopenfilename(filetypes=[("PNG Images", "*.png")])
    if path:
        overlay_path = path
        overlay_label.config(text=os.path.basename(path))

def cancel():
    global cancel_generation, generating
    cancel_generation = True
    generating = False
    print("[INFO] Генерацію скасовано")


def generate_images_thread():
    global generating
    if generating:
        return
    generating = True

    prompt = prompt_box.get("1.0", END).strip()

    # --- КРОК 5: Перевірка порожнього промпта ---
    if not prompt:
        messagebox.showerror("Помилка", "Промпт не може бути порожнім.")
        generating = False
        return
        
    # Завантажуємо CSV/JSON (якщо вибрано)
    params_list = None
    if 'csv_path' in globals() and csv_path:
        params_list = load_params(csv_path)
    count = int(count_entry.get())

    if not save_folder:
        messagebox.showerror("Помилка", "Будь ласка, оберіть папку для збереження.")
        generating = False
        return
    
    # --- Завантаження моделі один раз ---
    model_name = model_var.get()
    model_type, model_path = AVAILABLE_MODELS[model_name]

    global pipe, current_loaded_path
    from tools.generator import load_model

    # Завантажуємо тільки якщо змінилася модель
    if pipe is None or current_loaded_path != model_path:
        pipe = load_model(model_type, model_path)
        current_loaded_path = model_path

    for i in range(count):
        width = int(entry_width.get())
        height = int(entry_height.get())
        
        # Перевірка на кратність 64
        if width % 64 != 0 or height % 64 != 0:
            messagebox.showerror("Помилка", "SDXL вимагає width/height кратні 64.")
            generating = False
            return

        
        # Підстановка значень CSV у prompt
        if params_list:
            row = params_list[i % len(params_list)]
            try:
                prompt_i = prompt.format(**row)
            except KeyError:
                prompt_i = prompt
        else:
            prompt_i = prompt
        
        global cancel_generation
        if cancel_generation:
            messagebox.showinfo("Скасовано", "Генерацію зупинено користувачем.")
            generating = False
            cancel_generation = False
            return

        
        img = generate_image(
            prompt_i,
            width=width,
            height=height,
            model_type=model_type,
            model_path=model_path,
            pipe=pipe
        )
                        
        img = cut_center_transparent(img, overlay_path)

        filename = os.path.join(save_folder, f"gen_{i+1}.png")
        img.save(filename)
    
    start_button.config(state=NORMAL)


    messagebox.showinfo("Готово", f"Згенеровано {count} зображень.")
    generating = False

def start_generation():
    start_button.config(state=DISABLED)
    threading.Thread(target=generate_images_thread).start()


# --------------------- GUI ---------------------

window = Tk()
window.title("AI Generator")
window.geometry("500x680")

# --- Ctrl+V для Entry & Text ---
window.bind_class("Entry", "<Control-v>", lambda e: e.widget.event_generate("<<Paste>>"))
window.bind_class("Entry", "<Control-V>", lambda e: e.widget.event_generate("<<Paste>>"))
window.bind_class("Text", "<Control-v>", lambda e: e.widget.event_generate("<<Paste>>"))
window.bind_class("Text", "<Control-V>", lambda e: e.widget.event_generate("<<Paste>>"))

# Prompt
Label(window, text="Prompt:", font=("Arial", 12)).pack()
prompt_box = Text(window, height=5, width=50)
prompt_box.pack()

# Контекстне меню (ПКМ)
def show_context_menu(event):
    menu = Menu(window, tearoff=0)
    menu.add_command(label="Вставити (Ctrl+V)", command=lambda: event.widget.event_generate("<<Paste>>"))
    menu.tk_popup(event.x_root, event.y_root)

prompt_box.bind("<Button-3>", show_context_menu)

# Count
Label(window, text="Кількість зображень:", font=("Arial", 12)).pack()
count_entry = Entry(window, width=10)
count_entry.insert(0, "1")
count_entry.pack()

# Width / Height
size_frame = Frame(window)
size_frame.pack(pady=5)

Label(size_frame, text="Width:").grid(row=0, column=0, padx=5)
entry_width = Entry(size_frame, width=7)
entry_width.insert(0, "768")
entry_width.grid(row=0, column=1)

Label(size_frame, text="Height:").grid(row=0, column=2, padx=5)
entry_height = Entry(size_frame, width=7)
entry_height.insert(0, "1088")
entry_height.grid(row=0, column=3)

# Folder select
Button(window, text="Обрати папку збереження", command=select_folder).pack(pady=5)
folder_label = Label(window, text="(не вибрано)", fg="gray")
folder_label.pack()

# Overlay select
Button(window, text="Обрати оверлей (PNG)", command=select_overlay).pack(pady=5)
overlay_label = Label(window, text="(не вибрано)", fg="gray")
overlay_label.pack()

# CSV select
csv_path = ""

def select_csv():
    global csv_path
    path = filedialog.askopenfilename(filetypes=[("CSV / JSON Files", "*.csv *.json")])
    if path:
        csv_path = path
        csv_label.config(text=os.path.basename(path))

Button(window, text="Обрати CSV", command=select_csv).pack(pady=5)
csv_label = Label(window, text="(не вибрано)", fg="gray")
csv_label.pack()

from tkinter import StringVar, OptionMenu

model_var = StringVar(window)
model_var.set("RealVisXL (SDXL)")

Label(window, text="Оберіть модель:").pack(pady=5)
OptionMenu(window, model_var, *AVAILABLE_MODELS.keys()).pack(pady=5)


# Generate button
start_button = Button(window, text="ЗГЕНЕРУВАТИ", command=start_generation, bg="#28a745", fg="white", height=2)
start_button.pack(pady=20)
cancel_button = Button(window, text="СКАСУВАТИ", bg="#cc0000", fg="white", command=cancel)
cancel_button.pack(pady=5)


window.mainloop()
