IMAGEFULLNAME=twoyang0917/queryexporter

.PHONY: build push

build:
	docker build -t ${IMAGEFULLNAME} .

push:
	docker push ${IMAGEFULLNAME}

all: build push
