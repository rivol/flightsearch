# Flight search based on Kiwi.com

Personal helper scripts for finding flights with Kiwi.

## Usage

Create virtualenv and install packages from `requirements.txt`, then run:

    python main.py single TLL london_gb 2018-08-06 2018-08-13

To also make use of caching, ensure Redis is available before running the main script.
You can easily run Redis in Docker:

    docker run --rm -p 6379:6379 redis
