import tkinter
from tkinter import Button
from datetime import datetime
import time

standardTextSize = 30

def Draw():
    temps = tkinter.Label(text="Temps:", font=("Arial", standardTextSize))
    temps.place(relx= 0.10, rely= 0.11, anchor = 'center')
    tempf = tkinter.Label(text="100.0 °F", font=("Arial", standardTextSize))
    tempf.place(relx= 0.15, rely= 0.23, anchor = 'center')
    tempc = tkinter.Label(text="30.0 °C", font=("Arial", standardTextSize))
    tempc.place(relx= 0.15, rely= 0.35, anchor = 'center')
    humidity = tkinter.Label(text="Humidity: 60%", font=("Arial", standardTextSize))
    humidity.place(relx= 0.15, rely= 0.50,anchor = 'center')
    vpd = tkinter.Label(text="VPD: 1.006kPa", font=("Arial", standardTextSize))
    vpd.place(relx= 0.15, rely= 0.70, anchor = 'center')
    global text

    frame=tkinter.Frame(window,width=100,height=100,relief='solid',bd=1)
    frame.place(relx= 0.15, rely= 0.90, anchor = 'center')
    text=tkinter.Label(frame,text='Time:')
    text.pack()

    ac_button = Button(window, text="AC\n\nON", font=("Arial", 14), height = 10, width = 20, command=window.destroy)
    ac_button.place(relx= 0.42, rely= 0.79, anchor = 'center')

    humidifier = Button(window, text="Humidifier\n\nON", font=("Arial", 14), height = 10, width = 20, command=window.destroy)
    humidifier.place(relx= 0.65, rely= 0.79, anchor = 'center')

    dehumidifier = Button(window, text="Dehumidifier\n\nON", font=("Arial", 14), height = 10, width = 20, command=window.destroy)
    dehumidifier.place(relx= 0.88, rely= 0.79, anchor = 'center')

    '''
    exit_button = Button(window, text="Exit", height = 10, width = 20, command=window.destroy)
    exit_button.pack(pady=200)
    '''

def ReadValues():
    #read i2c values
    print("UPDATING SENSOR VALUES")
    window.after(1000, Refresher)


def Refresher():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    global text
    text.configure(text=("Time: " + current_time), font=("Arial", standardTextSize))
    second_time = now.strftime("%S")
    print(second_time)
    if int(second_time) % 15 == 0:
        print("CALLING i2c")
        window.after(1000, ReadValues)
    else:
        window.after(1000, Refresher)

window = tkinter.Tk()
window.geometry("1024x600")

Draw()
Refresher()

window.mainloop()