from neurosdk.scanner import Scanner
from neurosdk.sensor import Sensor
from callibri_v2 import onCallibriSignalDataReceived, find_sensors
from neurosdk.scanner import Scanner
from neurosdk.cmn_types import SensorFamily, SensorCommand
import numpy as np
import pygame
import matplotlib.pyplot as plt
import random
import sys
import time
import datetime

######## this allows to save incoming signal from callback function right in the Sensor instance
Sensor.data = np.array([])

def draw_text_in_the_middle(text: str, 
                            color: pygame.Color | tuple[int,int,int],
                            screen: pygame.Surface, 
                            font: pygame.font.Font) -> None:
    """Note: newlines not ignored"""

    text_lines = text.split('\n')
    WIDTH, HEIGHT = screen.get_size()
    for i, line in enumerate(text_lines):
        line_size = font.size(line)
        screen.blit(
            font.render(line, True, color),
            ((WIDTH - line_size[0])//2, (HEIGHT + line_size[1] * i * 2)//2)
            )
        
####### Connect to callibri #######
scanner = Scanner([SensorFamily.LECallibri])
scanner.start()
sensor_info = find_sensors(scanner)[0]
sensor = scanner.create_sensor(sensor_info)
sensor.signalDataReceived = onCallibriSignalDataReceived
sensor.connect()
sensor.exec_command(SensorCommand.StartSignal)

WIDTH, HEIGHT = (1200, 800)
SAMPLING_FREQUENCY = 1000
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,0,255)
ORANGE = (255,165,0)




pygame.init()
pygame.font.init()
 

###### Greeting ######
screen = pygame.display.set_mode((WIDTH,HEIGHT))
font: pygame.font.Font = pygame.font.SysFont(pygame.font.get_default_font(), WIDTH*HEIGHT//20000)
GREETING_TEXT = "Для начала пройдите калибровку.\nСледуйте указаниям. Чтобы продолжить, нажмите любую клавишу!"
screen.fill(BLACK)  
draw_text_in_the_middle(GREETING_TEXT, WHITE, screen, font)
pygame.display.flip()

greeting = True
while greeting:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit(0)
        elif event.type == pygame.KEYDOWN:
            greeting = False


##### Setting speed #####
epoch_time = 1
epoch_size = epoch_time * SAMPLING_FREQUENCY
#TODO: Make changing symbol typing speed available. 


###### Getting noise value ######
NO_BLINKING_TIME = 0.1
PREPARING_FOR_NO_BLINKING_TEXT = (f"Вам нужно будет не моргать и сидеть спокойно {NO_BLINKING_TIME} секунд.\n "
                                   "Как будете готовы, нажмите любую клавишу.")
NO_BLINKING_TEXT = ("Не моргайте. Осталось time_left секунд..")
screen.fill(BLACK)
draw_text_in_the_middle(PREPARING_FOR_NO_BLINKING_TEXT, WHITE, screen, font)
pygame.display.flip()

#preparing
preparing_for_no_blinking = True
while preparing_for_no_blinking:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit(0)
        elif event.type == pygame.KEYDOWN:
            preparing_for_no_blinking = False

#getting noise value
noise_data = []
start = time.time()
end = start + NO_BLINKING_TIME
time_left = NO_BLINKING_TIME
while time_left > 0:
    screen.fill(ORANGE)
    draw_text_in_the_middle(NO_BLINKING_TEXT.replace('time_left',str(round(time_left))), WHITE, screen, font)
    pygame.display.flip()
    noise_data.extend(sensor.data)
    time_left = end - time.time()
noise_value = np.max(noise_data)
#TODO: Check that user really was calm by standard deviation or something

##### Getting thresholds on generated data #####
#preparing
PREPARING_FOR_CALIBRATING_TEXT = "Далее вам будет дана последовательность символов, \nкоторые вам нужно будет ввести.\n" \
                                "Постарайтесь моргать с одинаковой силой для каждого типа символа."
screen.fill(BLACK)
draw_text_in_the_middle(PREPARING_FOR_CALIBRATING_TEXT, WHITE, screen, font)
pygame.display.flip()

preparing_for_calibrating = True
while preparing_for_calibrating:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit(0)
        elif event.type == pygame.KEYDOWN:
            preparing_for_calibrating = False


#getting thresholds
TEST_DATA_LENGTH = 10
test_morse: str = ''.join([random.choice(('*')*3 + ('-')*3 + ('.')) for _ in range(TEST_DATA_LENGTH)]) # make chances of appearance of dot or dash higher
screen.fill(ORANGE)
draw_text_in_the_middle(''.join(test_morse), WHITE, screen, font)
pygame.display.flip()

epoch_dash_signals: list[list[float]] = []
epoch_dot_signals: list[list[float]] = []
epoch: list[float] = []

for i, symbol in enumerate(test_morse):
    start = time.time()
    while time.time() < start + epoch_time:
        epoch.extend(sensor.data)
    #FIXME: drawing completed data is terrible now
    indicator = [' '] * TEST_DATA_LENGTH
    indicator[i] = '-' # indicate current symbol
    draw_text_in_the_middle(''.join(test_morse) + '\n' + ''.join(indicator), WHITE, screen, font)
    pygame.display.flip()
    if symbol == '-':
        epoch_dash_signals.append(epoch)
    elif symbol == '*':
        epoch_dot_signals.append(epoch)
    epoch = []

#calculate thresholds by mean. 
#TODO:  Find optimal constant to make the thresholds lower for accepting weaker user input.
ACCEPTABLE_BLINK_ERROR = 0
#np.mean can't be used because arrays are inhomgenous
dash_threshold = sum([max(epoch) for epoch in epoch_dash_signals])  / len(epoch_dash_signals) - ACCEPTABLE_BLINK_ERROR
dot_threshold  = sum([max(epoch) for epoch in epoch_dot_signals])  /  len(epoch_dot_signals)  - ACCEPTABLE_BLINK_ERROR

#plot and research

axes = [plt.subplot(100 * (i+1)) for i in range(len(epoch_dash_signals))]
for i, dash_epoch in enumerate(epoch_dash_signals):
    axes[i].plot(range(len(dash_epoch)), dash_epoch)
    axes[i].plot(range(len(dash_epoch)), [dash_threshold] * len(dash_epoch), 'red')

plt.title("Dash epochs")
plt.tight_layout()
plt.show()

axes = [plt.subplot(100 * (i+1)) for _ in range(len(epoch_dash_signals))]
for i, dot_epoch in enumerate(epoch_dot_signals):
    axes[i].plot(range(len(dot_epoch)), dot_epoch)
    axes[i].plot(range(len(dot_epoch)), [dot_threshold] * len(dot_epoch), 'red')

plt.title("Dot epochs")
plt.tight_layout()
plt.show()

###########
del scanner
del sensor
pygame.quit()