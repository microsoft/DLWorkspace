FROM golang:1.13-alpine as builder

WORKDIR /scheduler-src

COPY src /scheduler-src
RUN go mod download

RUN go build -o dlts-scheduler /scheduler-src/main.go

FROM alpine:3.10.1

RUN apk update && apk add --no-cache bash
COPY --from=builder /scheduler-src/dlts-scheduler /usr/local/bin

ENTRYPOINT ["/usr/local/bin/dlts-scheduler"]
