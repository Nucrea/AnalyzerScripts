@cd python
@python "worker.py" "-set_tenzo_coefficients"
pause


REM avr-gcc -g -Os -mmcu=atmega328p  -c main.c  -o output/main.bin
REM avr-objcopy -j .text -j .data  -O ihex output/main.bin output/main.hex
REM pause
REM avrdude -p attiny13 -c usbasp -U flash:w:main.hex:i -F -P usb
