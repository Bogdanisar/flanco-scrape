
# Flanco web scraper

Retailers are sometimes known to trick their customers by first raising the price of the product and then displaying it as being on sale even though the reduced price is the same as before. This might be done for occasions such as Black Friday.

[Flanco](https://www.flanco.ro) is a romanian online retailer and they do promotions. We want to verify that they operate in good faith in regards to their pricing. The idea is to periodically index the products and their prices and store them. We do this by scraping the website on command using Python and the Selenium library. We do this in Docker containers. The informations are stored in CSV files.

The main script is `./src/flanco_scrape.py`. It can be run in four modes. In order to change the behaviour for docker-compose, check the `entrypoint` option in `compose.yaml`.
The four modes are:
- `list`: A list of product ids is provided on the command line and the script only scrapes the prices of these products.
- `test`: Like the `list` mode, except the product ids are hardcoded into the script. Since these ids might become obsolete, it's possible that the script will fail. Use `list` instead.
- `category`: An entire category of products will be parsed. A relative website URL must be provided on the command line. Example: `./flanco_scrape.py category electrocasnice-mari/aparate-frigorifice/combine-frigorifice.html`.
- `entire`: The script will attempt to scrape all products on the website.

Other script options can be seen by running `./flanco_scrape.py -h`.


### Output

When running locally, the output can be found in `./src/shared_dir/flanco_csv`.

When running with docker-compose, the output is stored in a docker volume created from the compose.yaml file. You can find where this is located running the following commands. Note: They might provide different results for non-root/root users, so you might need to run them with `sudo` to find the volume:
- `docker volume ls`.

The volume name might be `practica-flanco_flanco_scrape`, in which case run:
- `docker inspect practica-flanco_flanco_scrape`.


# Running with docker-compose

Before using docker-compose, it might be necessary to start the docker service with `[sudo] service docker restart`.

First, build the necessary images with:
- `docker-compose -f compose.yaml build`.
- If there are errors when running the previous command after the first time, try `docker-compose -f compose.yaml build --no-cache --pull`.

Then, run the containers together:
- `docker-compose -f compose.yaml up --abort-on-container-exit`


# Running locally on Selenium container (Easier to use when developing. Instructions for Ubuntu)

Here, we want to run the script locally on the development machine, but have the Selenium browser running in a docker container. This is more convenient when working on the script than starting up the containers with docker-compose.

First, get the dependencies on the local machine:
- `sudo apt-get install python3-pip -y`
- `sudo pip install selenium requests webdriver-manager --upgrade`

Second, get the Selenium image and start a container from it:
- `docker pull selenium/standalone-chrome:latest`
- `docker run -p 4445:4444 -p 7901:7900 --shm-size="2g" selenium/standalone-chrome:latest`

Third, execute the script. For instance, run: `./flanco_scrape.py -vv category electrocasnice-mari/aparate-frigorifice/combine-frigorifice.html`


# Running locally with GUI (Best for debugging. Instructions for Ubuntu)

This is slower than the other modes, but running with a GUI can be useful when debugging.

First, ensure the dependencies are available on the local Ubuntu machine as in the previous section.

Second, make sure that Chrome is installed and updated to the latest version:
`sudo apt-get install google-chrome-stable`

Finally, make sure the `--run-locally` flag is enabled when running the script on the development machine. For example, one can run: `./flanco_scrape.py -vv --run-locally test`.

