FROM golang:1.13-alpine as builder

WORKDIR /scheduler-src

COPY src/go.mod src/go.sum /scheduler-src/
RUN go mod download

COPY src/*.go /scheduler-src/
RUN go build -o dlts-scheduler /scheduler-src/

FROM alpine:3.10.1

RUN apk update && apk add --no-cache bash
COPY --from=builder /scheduler-src/dlts-scheduler /usr/local/bin

ENTRYPOINT ["/usr/local/bin/dlts-scheduler"]
