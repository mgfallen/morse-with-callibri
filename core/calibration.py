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

######## it allows to save incoming signal right in the Sensor instance
Sensor.data = []

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
epoch_time = 0.5
epoch_size = epoch_time * SAMPLING_FREQUENCY
#TODO: Make changing symbol typing speed available. 
#FIXME: indicating speed requires checking exact time, that python can't handle fast


###### Getting noise value ######
NO_BLINKING_TIME = 0
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
high_threshold = 0
low_threshold = 0
TEST_DATA_LENGTH = 15
test_morse: str = ''.join([random.choice(('*','-',' ')) for _ in range(TEST_DATA_LENGTH)])

screen.fill(ORANGE)
draw_text_in_the_middle(''.join(test_morse), WHITE, screen, font)
pygame.display.flip()

completed_morse: str = ''
epoch_signals: list[list[float]] = []
epoch: list[float] = []
for symbol in test_morse:
    start = time.time() + datetime.datetime.now().microsecond/1e6
    while time.time() + datetime.datetime.now().microsecond/1e6 < start + epoch_time:
        epoch.extend(sensor.data)
        ...
    completed_morse += symbol
    draw_text_in_the_middle(''.join(test_morse), WHITE, screen, font)
    draw_text_in_the_middle(completed_morse + '_' * (len(test_morse) - len(completed_morse)), # make completed symbols be green
                            GREEN, screen, font) 
    pygame.display.flip()
    epoch_signals.append(epoch)
del scanner
del sensor
pygame.quit()