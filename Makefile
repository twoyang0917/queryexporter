IMAGEFULLNAME=twoyang0917/queryexporter

.PHONY: build buildx push

build:
	docker build -t ${IMAGEFULLNAME} .

# apple silicon
buildx:
	docker buildx build --platform linux/amd64 --load -t ${IMAGEFULLNAME} .

push:
	docker push ${IMAGEFULLNAME}

all: buildx push
