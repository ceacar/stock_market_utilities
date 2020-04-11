NAME := stock_utility
TAG	:= $(shell date '+%Y%m%d%H%M%S')
IMG	:= ${NAME}:${TAG}
LATEST := ${NAME}:latest

.PHONY: build push

build:
	@docker build -t ${IMG} .
	@docker tag ${IMG} ${LATEST}

push:
	@docker push ${NAME}

test:
	py.test ./tests/test_* --disable-pytest-warnings -vv

itest:
	py.test ./tests/itest_* --disable-pytest-warnings -vv

pitest:
	while true;do inotifywait -r -e close_write ${PWD} && { py.test ${PWD}/tests/itest_*.py --disable-pytest-warnings -vv; echo "tested"; };sleep 1;done

ptest:
	while true;do inotifywait -r -e close_write ${PWD} && { py.test ${PWD}/tests/test_*.py --disable-pytest-warnings -vv; echo "tested"; };sleep 1;done
