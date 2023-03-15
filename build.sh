#!/bin/bash

docker buildx build -t kjwon15/kmastodon-status --cache-from kjwon15/kmastodon-status:cache --cache-to kjwon15/kmastodon-status:cache --push .
