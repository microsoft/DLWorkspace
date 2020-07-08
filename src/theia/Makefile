.PHONY: build clean

build:
	yarn install --frozen-lockfile
	yarn run theia build
	yarn install --production --frozen-lockfile --check-files
	rm -rf node_modules/.cache
	tar czvf theia.tgz --exclude theia.tgz *

clean:
	ls --directory */ | xargs rm -rf
	rm -rf *.tgz *.js
