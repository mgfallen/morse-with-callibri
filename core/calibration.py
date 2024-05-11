import neurosdk.scanner
from callibri_v2 import onCallibriSignalDataReceived, find_sensors
from neurosdk.cmn_types import SensorFamily, SensorCommand
from neurosdk.sensor import Sensor
import numpy as np
import pygame
import matplotlib.pyplot as plt
import sys
import time

######## it allows to save incoming signal right in the Sensor instance
Sensor.data = []

def draw_text_in_the_middle(text: str, 
                            color: pygame.Color | tuple[int,int,int],
                            screen: pygame.Surface, 
                            font: pygame.font.Font) -> None:
    """Note: newlines supported, although pygame doesn't"""

    text_lines = text.split('\n')
    WIDTH, HEIGHT = screen.get_size()
    for i, line in enumerate(text_lines):
        line_size = font.size(line)
        screen.blit(
            font.render(line, True, WHITE),
            ((WIDTH - line_size[0])//2, (HEIGHT + line_size[1] * i * 2)//2)
            )
        
####### Connect to callibri #######
scanner = neurosdk.scanner.Scanner([SensorFamily.LECallibri])
scanner.start()
sensor_info = find_sensors(scanner)[0]
sensor = scanner.create_sensor(sensor_info)
sensor.signalDataReceived = onCallibriSignalDataReceived
sensor.connect()
sensor.exec_command(SensorCommand.StartSignal)
    
WIDTH, HEIGHT = (1200, 800)
SAMPLING_FREQUENCY = 9600
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

###### Getting noise value ######
NO_BLINKING_TIME = 7
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

###### Getting thresholds ######
PREPARING_FOR_CALIBRATION_TEXT = "Далее вам нужно будет моргать для обозначения точек или тире. \n" \
                            "Как будете готовы, нажмите любую клавишу."
PROMPTING_DOT_BLINK_TEXT = "." + '\n'*7 + '(точка)'
PROMPTING_DASH_BLINK_TEXT = "-" + '\n'*7 + '(тире)'
USER_ACCURACY = ("Ваша погрешность моргания для точки: dot_blink_error.\n"
                "Для тире: dash_blink_error\n"
                "Чтобы продолжить, нажмите Пробел.\n"
                "Чтобы завершить, нажмите Escape.")
USER_HIGH_ACCURACY_REPORT = ("Погрешность моргания достаточно низкая!\n"
                             "Вы можете завершить калибровку")
USER_LOW_ACCURACY_REPORT = ("Погрешность моргания пока высокая."
                            "Продолжайте калибровку.")

OPTIMAL_DEVIATION = 30 # optimal difference between two epoch threshold. low deviation shows that user is blinking with persistently same values
OPTIMAL_ITERATIONS = 5 # user will likely start giving persistent blinks within this iteration amount
ITERATION_SIZE = 10 # amount of prompted dash or dots within an iteration
MIN_PROMPT_INTERVAL= 0.5
MAX_PROMPT_INTERVAL = 2

#preparing
screen.fill(BLACK)
draw_text_in_the_middle(PREPARING_FOR_CALIBRATION_TEXT, WHITE, screen, font)
pygame.display.flip()

preparing_for_calibration = True
while preparing_for_calibration:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit(0)
        elif event.type == pygame.KEYDOWN:
            preparing_for_calibration = False

dot_threshold = 0
dash_threshold = 0

iteration = 1
#fill with garbage to avoid errors with computing deviation on first iteration
dot_threshold_peaks = [1000]
dash_threshold_peaks = [1000]

dot_blink_error = 1000
dash_blink_error = 1000

#calibrating
calibrating = True
while calibrating:
    for epoch in range(ITERATION_SIZE):
        epoch_data = []
        mode = np.random.random() < 0.5 # prompting dot or dash
        text = PROMPTING_DOT_BLINK_TEXT if mode == 0 else PROMPTING_DASH_BLINK_TEXT
        screen.fill(ORANGE)
        draw_text_in_the_middle(text, BLACK, screen, font)
        #make a line that appears and dissapears instantly for user to react
        pygame.display.flip()
        interval = np.random.uniform(MIN_PROMPT_INTERVAL, MAX_PROMPT_INTERVAL) # for user to get persistent in different intervals between blinks.

        start = time.time()
        end = start + interval
        time_left = interval
        while time_left > 0:
            epoch_data.extend(sensor.data)
            time_left = end - time.time()
        (dot_threshold_peaks if mode == 0 else dash_threshold_peaks).append(np.max(epoch_data)) 

        screen.fill(ORANGE) # for message to dissapear. it will make user react on next message better
        pygame.display.flip()

    screen.fill(BLUE)

    last_dot_blink_error = dot_blink_error
    last_dash_blink_error = dash_blink_error
    dot_blink_error = np.round(np.std(dot_threshold_peaks),2)
    dash_blink_error = np.round(np.std(dash_threshold_peaks),2)
    dot_deviation = np.abs(dot_threshold_peaks[-2] - dot_threshold_peaks[-1])
    dash_deviation = np.abs(last_dash_blink_error - dash_blink_error)

    accuracy_report = (USER_HIGH_ACCURACY_REPORT 
                       if dot_deviation < OPTIMAL_DEVIATION and dash_deviation < OPTIMAL_DEVIATION
                  else USER_LOW_ACCURACY_REPORT)

    dot_threshold = np.mean(dot_threshold_peaks)
    dash_threshold = np.mean(dash_threshold_peaks)

    #persistence of user blink strength
    #NOTE: accuracy is counted on all calibration epochs, not current one
    print('peaks',dot_threshold_peaks, dash_threshold_peaks)
    print()
    draw_text_in_the_middle(
        USER_ACCURACY.replace("dot_blink_error", str(dot_convergence)).replace("dash_blink_error", str(dash_convergence)) + '\n' + accuracy_report,
        WHITE,
        screen,
        font
        ) 
    pygame.display.flip()

    waiting_to_proceed = True
    while waiting_to_proceed:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                match event.key:
                    case pygame.K_ESCAPE:
                        waiting_to_proceed = False
                        calibrating = False
                    case pygame.K_SPACE:
                        waiting_to_proceed = False
                         

    iteration += 1

del scanner
del sensor
pygame.quit()