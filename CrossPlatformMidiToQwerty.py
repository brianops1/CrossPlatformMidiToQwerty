# packages

#msvcrt
#keyboard

import math,re,mido,os,mido.backends.rtmidi
from threading import Thread
from pynput import keyboard
from pynput.keyboard import Key, Controller
from time import sleep

# Static variables

Board = Controller()

ListenerKey = None
ListenerThread = None
floor = math.floor
press = Board.press
release = Board.release

currentPort = None

velocityMap = "1234567890qwertyuiopasdfghjklzxc"
lastvel = "c"

letterNoteMap = "1!2@34$5%6^78*9(0qQwWeErtTyYuiIoOpPasSdDfgGhHjJklLzZxcCvVbBnm"
LowNotes = "1234567890qwert"
HighNotes = "yuiopasdfghj"

sustainToggle = False
MainLoop = True
CloseThread = False

SettingsFileName = "MidiTranslatorSettings"

PressedKeys = {}

# Savable Variables

SavableSettings = {"sustainEnabled":True,"noDoubles":True,"simulateVelocity":True,"88Keys":True,"sustainCutoff":63}

# functions


def select_port():
    global currentPort
    if currentPort:
        currentPort.close()
    print("Select input device:")
    inputports = mido.get_input_names()
    for portNumber, portName in enumerate(inputports):
        print(str(portNumber+1)+": "+portName)
    while True:
        selectedport = int(input("(enter a number from 1 to "+str(len(inputports))+")\n"))-1
        if 0 <= selectedport < len(inputports):
            break
        else:
            print("Please select a valid input device.")
    print("Selected "+inputports[selectedport])
    return inputports[selectedport]


def find_velocity_key(V):
    global lastvel
    try:
        Index = 4 * round(V/4)
        Key = velocityMap[int(Index/4)]
        Orgin = Index
        lastvel = Key
    except:
        Key = lastvel
    '''
    while Index >= Orgin - 12: 
        V -= 4
        Index = 4 * round(V/4)
        Key = velocityMap[int(Index/4)]
        
    while Index <= Orgin + 12:
        V += 4
        Index = 4 * round(V/4)
        Key = velocityMap[int(Index/4)]
    '''
        
    #these while checks are so the program won't hit a note
    #that is pressed just to change velocity
    #At least it should've but it doesn't work :(
        
    return Key


def simulate_key(type, note, velocity):
    if not (-15 <= note-36 <= 88):
        return
    index = note - 36
    key = 0
    try:
        key = letterNoteMap[index]  # C1 is note 36, C6 is note 96
    except:
        pass
    if type == 'note_on':
        
            if SavableSettings["simulateVelocity"]:
                velocitykey = find_velocity_key(velocity)
                if velocitykey:
                    press(Key.alt)
                    press(velocitykey)
                    release(velocitykey)
                    release(Key.alt)

            if (0 <= note-36 <= 60):
                if SavableSettings["noDoubles"]:
                    if re.search('[!@$%^*(]', key):
                        release(letterNoteMap[index-1])
                    else:
                        release(key.lower())
                if re.search('[!@$%^*(]', key):
                    press(Key.shift)
                    press(letterNoteMap[index-1])
                    release(Key.shift)
                elif key.isupper():
                    press(Key.shift)
                    press(key.lower())
                    release(Key.shift)
                else:
                    press(key)
            elif SavableSettings["88Keys"]:
                K = None
                if note >= 20 and note < 40:
                    K = LowNotes[note - 21]
                else:
                    K = HighNotes[note - 109]
                if K:
                    release(K.lower())
                    press(Key.ctrl)
                    press(K.lower())
                    release(Key.ctrl)
                        
    else:
        if (0 <= note-36 <= 60):
            if re.search('[!@$%^*(]', key):
                release(letterNoteMap[index-1])
            else:
                release(key.lower())
        else:
            if note >= 20 and note < 40:
                K = LowNotes[note - 21]
            else:
                K = HighNotes[note - 109]
            release(K.lower())


def parse_midi(message):
    global sustainToggle
    if message.type == 'control_change' and SavableSettings["sustainEnabled"]:
        if not sustainToggle and message.value > SavableSettings["sustainCutoff"]:
            sustainToggle = True
            press(Key.space)
        elif sustainToggle and message.value < SavableSettings["sustainCutoff"]:
            sustainToggle = False
            release(Key.space)
    elif (message.type == 'note_on' or message.type == 'note_off'):
        if message.velocity == 0:
            simulate_key('note_off', message.note, message.velocity)
        else:
            simulate_key(message.type, message.note, message.velocity)

def Main():
    global CloseThread
    print("Now listening to note events on "+str(currentPort)+"...")
    for message in currentPort:
        parse_midi(message)
        if CloseThread:
            break
    CloseThread = False


##############################

def Settings():
    global SavableSettings,currentPort
    chang = True
    while chang:
        Clear()
        print('''
Which settings would you like to change?

0. Back

1. Sustain Enabled ('''+str(SavableSettings["sustainEnabled"])+''')

2. Double Notes Disabled ('''+str(SavableSettings["noDoubles"])+''')

3. Velocity Enabled ('''+str(SavableSettings["simulateVelocity"])+''')

4. 88 Keys Enabled ('''+str(SavableSettings["88Keys"])+''')

5. Sustain Pedal Cutoff/Offset ('''+str(SavableSettings["sustainCutoff"])+''')

6. Change Midi Port ('''+str(currentPort)+''') ''')
        t = None
        try:
            t = int(input())
            if t > 6 or t < 0:
                t = None
        except:
            t = None

        if t != None:
            if t == 0:
                Clear()
                chang = False
            elif t == 1:
                SavableSettings["sustainEnabled"] = not SavableSettings["sustainEnabled"]
            elif t == 2:
                SavableSettings["noDoubles"] = not SavableSettings["noDoubles"]
            elif t == 3:
                SavableSettings["simulateVelocity"] = not SavableSettings["simulateVelocity"]
            elif t == 4:
                SavableSettings["88Keys"] = not SavableSettings["88Keys"]
            elif t == 5:
                SavableSettings["sustainCutoff"] = IntAsk("\nEnter what offset you would like to use (0-127)")
            elif t == 6:
                currentPort = mido.open_input(select_port())
                
            Save()
        else:
            print('\nError, try again\n')
            sleep(.5)



def LoadFiles():
    global SavableSettings
    try:
        f = open(SettingsFileName+'.txt',"r")
        it = 0
        Changing = None
        for i in f.read().split('\n'):
            it += 1
            if it % 2 == 1:
                Changing = i 
            else:
                try:
                    SavableSettings[str(Changing)] = int(i)
                except:
                    SavableSettings[str(Changing)] = i
                    if SavableSettings[str(Changing)] == "True":
                        SavableSettings[str(Changing)] = True
                    elif SavableSettings[str(Changing)] == "False":
                        SavableSettings[str(Changing)] = False
                    
        f.close()
    except:
        Save()
        
####

def Save():
    File = open(SettingsFileName+'.txt','w')
    it = 0
    for i,v in SavableSettings.items():
        it += 1
        if it != 1:
            File.write('\n'+str(i)+'\n')
        else:
            File.write(str(i)+'\n')
        File.write(str(v))
    File.close()

####

def Clear():
  if os.name == 'nt':
    os.system('cls')
  else:
    os.system('clear')

def IntAsk(text):
    var = None
    while var == None:
        try:
            var = int(input(text))
        except:
            print('\nThere was an issue\n')
            var = None

    return var

# initialize key detection #

def on_press(Key):
    pass
    

def on_release(Key):
    global ListenerKey
    try:
        if Key.char:
            ListenerKey = Key.char
            return False
    except:
        pass

def DetectKey():
    with keyboard.Listener(
        on_press=on_press,
        on_release=on_release) as listener:
            listener.join()
    return ListenerKey






# initialize main #

try:
    LoadFiles()
    currentPort = mido.open_input(select_port())
    
    while MainLoop:
        Clear()
        print('   ---Welcome to the menu---\n\n\n1. Run main program\n\n2. Settings')
        t = None
        try:
            t = int(input())
            if t > 2 or t < 1:
                t = None
        except Exception as E:
            print(E)
            t = None

        if t:
            Clear()
            if t == 1:
                while currentPort.poll():
                    pass
                Clear()
                Thread(target = Main).start()
                sleep(.5)
                input('Main code is now running\nhit enter to go back to the menu at any time')
                CloseThread = True
            elif t == 2:
                Clear()
                Settings()
                
        else:
            Clear()
            print('There seemed to be an issue')
            
except Exception as E:
    Clear()
    print('Error detected')
    input(E)
input('\n\nHit enter now to close')
