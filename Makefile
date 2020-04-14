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

intraday:
	while true;do ./run_mini_midas.py get_intraday_data AAPL,TSLA,DVAX,IAU | tee /tmp/run_mini_midas_intraday_${date +%Y%m%d%H%M%S}.log;sleep 5;done

plot:
	while true;do ./run_mini_midas.py plot AAPL,TSLA,DVAX,IAU | tee /tmp/run_mini_midas_plot_${date +%Y%m%d%H%M%S}.log;sleep 5;done

historical:
	./run_mini_midas.py get_historical_data AAPL,TSLA,DVAX,IAU 
