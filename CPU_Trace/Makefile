CC = gcc
CFLAGS = -Wall -Wextra -g -I./include
LDFLAGS = -lczmq -ldw -lelf -lnvidia-ml

dw-pid: src/dw-pid.c
	$(CC) $(CFLAGS) -o dw-pid src/dw-pid.c $(LDFLAGS)

dw: dw.c
	$(CC) $(CFLAGS) -o dw dw.c $(LDFLAGS)

clean:
	rm -f dw

.PHONY: clean
