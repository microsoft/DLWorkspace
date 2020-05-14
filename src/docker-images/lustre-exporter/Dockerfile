FROM golang:1.14.2 as builder

# https://github.com/HewlettPackard/lustre_exporter
ENV VERSION=v2.0.0
RUN go get github.com/HewlettPackard/lustre_exporter && \
    cd $GOPATH/src/github.com/HewlettPackard/lustre_exporter && \
    git checkout ${VERSION} && sed -i 's/GOLINTER_OPT    ?= --vendor --deadline 6m --cyclo-over=20 --disable=aligncheck --disable=gosimple --disable=gotype/GOLINTER_OPT    ?= --vendor --deadline 6m --cyclo-over=20 --disable=aligncheck --disable=gosimple --disable=gotype --errors/g' Makefile && \
    make && \
    cp lustre_exporter /tmp

FROM centos:7

COPY --from=builder /tmp/lustre_exporter /
CMD /lustre_exporter
