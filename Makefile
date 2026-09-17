.PHONY: build shell turtlesim teleop describe clean

GUIX := guix time-machine -C channels.scm --max-jobs=1 --
CONTAINER := $(GUIX) shell -m manifest.scm --container --network \
	--preserve=DISPLAY --expose=/tmp/.X11-unix

build:
	$(GUIX) build -m manifest.scm

shell:
	$(CONTAINER) -- bash

turtlesim:
	./scripts/run-in-guix-container turtlesim_node

teleop:
	./scripts/run-in-guix-container turtle_teleop_key

describe:
	$(GUIX) describe

clean:
	@echo 'Guix owns build results in /gnu/store; use guix gc deliberately if needed.'
