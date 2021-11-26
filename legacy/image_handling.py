from PIL import Image
import requests
import logging
import imagehash
import os
import cv2
import pytesseract

import config
import crawler.url_handling

def image_optical_character_recognition(item):
	file_path = os.path.join(item)
	raw_image = cv2.imread(file_path)
	# if file not in db
	# img = cv2.resize(raw_image, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
	# make image grey
	img = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)
	#img = cv2.blur(img,(5,5))
	# apply threshold to make image binary
	#ret, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
	# save image
	cv2.imwrite(os.path.expanduser("~/img_cache/") + file_path.split("/")[-1], img)
	# add image to db
	tesseract_image = pytesseract.image_to_string(Image.open(os.path.expanduser("~/img_cache/") + file_path.split("/")[-1]))

	return tesseract_image

def crawl_images(images_indexed, published_on, cursor, full_url, discovered_urls, broken_urls, site_url, images=[], image_urls=[]):
	for i in images:
		ocr_result = ""
		# Only crawl and index my own images for now
		# This would need to be removed if I wanted to index other websites
		if site_url in full_url:
			try:
				if i.get("src") and i.get("src") not in image_urls:
					if i["src"].startswith("/") and not i["src"].startswith("//"):
						image_url_to_get = "https://{}".format(site_url) + i["src"]
					elif i["src"].startswith("//"):
						image_url_to_get = "https:" + i["src"]
					else:
						image_url_to_get = i["src"]

					# Filter out query params
					image_url_to_get = image_url_to_get.split("?")[0]

					image_urls.append(image_url_to_get)

					file_name = "/home/james/Projects/jamesg-search/static/images/{}".format(i["src"].split("/")[-1].split("?")[0])

					md5_checksum = ""

					if not os.path.isfile(file_name):
						session = requests.Session()
						session.max_redirects = 3

						head_request = session.head(image_url_to_get, headers=config.HEADERS)

						if head_request.status_code == 200 and ("Content-Type" in head_request.headers and not "image" in head_request.headers["Content-Type"]):
							logging.info("Image is not an image, skipping")
							crawler.url_handling.log_error(image_url_to_get, "Unknown", "Image is not an image, skipping.", discovered_urls, broken_urls, full_url)
							continue

						try:
							download_image = requests.get(image_url_to_get, stream=True, headers=config.HEADERS)
						except requests.exceptions.Timeout:
							crawler.url_handling.log_error(image_url_to_get, "Unknown", "Image URL timed out.", discovered_urls, broken_urls, full_url)
							continue
						except requests.exceptions.TooManyRedirects:
							crawler.url_handling.log_error(image_url_to_get, "Unknown", "Image URL redirected too many times (more than 3 times).", discovered_urls, broken_urls, full_url)
							continue
						except:
							crawler.url_handling.log_error(image_url_to_get, "Unknown", "Error retrieving image.", discovered_urls, broken_urls, full_url)
							continue

						if download_image.status_code == 200:

							# Get only file name, not full path

							image_file = Image.open(download_image.raw)

							image_file.save(file_name)

							#ocr_result = image_optical_character_recognition(file_name)

							md5_checksum = imagehash.average_hash(image_file)

							# check if md5_checksum is already in the database
							checksum_in_db = cursor.execute("SELECT md5_checksum FROM images WHERE md5_checksum = ? LIMIT 1;", (str(md5_checksum),)).fetchone()

							if checksum_in_db:
								crawler.url_handling.log_error(image_url_to_get, download_image.status_code, "Image already in database because it is being used on another page. Will not add again.", discovered_urls, broken_urls, full_url)

								continue
								
							image_file.thumbnail((300,300))

							image_file.save(file_name)

							size_of_image = len(download_image.content)

							# if image size is greater than 1 mb
							if size_of_image > 1000000:
								crawler.url_handling.log_error(image_url_to_get, 200, "Image size is {} bytes (too large).".format(size_of_image), discovered_urls, broken_urls, full_url)
								continue
						else:
							crawler.url_handling.log_error(image_url_to_get, download_image.status_code, "Image could not be retrieved.", discovered_urls, broken_urls, full_url)

							print("{} does not exist.".format(image_url_to_get))
							logging.warning("{} does not exist.".format(image_url_to_get))

							continue

					md5_checksum = str(md5_checksum)
					
					check_if_indexed = cursor.execute("SELECT COUNT(image_src) FROM images WHERE image_src = ?", (image_url_to_get,)).fetchone()[0]

					caption = ""

					# if parent is figure, search for a figcaption
					if i.parent and i.parent.name == "figure":
						for j in i.parent.children:
							if j.name == "figcaption":
								caption = j.text

					if i.get("alt") == None or i.get("alt") == "":
						crawler.url_handling.log_error(image_url_to_get, 200, "Image is missing an alt tag.", discovered_urls, broken_urls, full_url)

					if i.get("alt") and len(i["alt"]) > 150:
						crawler.url_handling.log_error(image_url_to_get, download_image.status_code, "Image alt text is {} characters (too long).".format(len(i["alt"])), discovered_urls, broken_urls, full_url)

					if check_if_indexed == 0:
						if published_on != None:
							cursor.execute("INSERT INTO images VALUES (?, ?, ?, ?, ?, ?, ?)", (full_url, i["alt"], image_url_to_get, published_on["datetime"].split("T")[0], md5_checksum, caption, ocr_result, ))
						else:
							cursor.execute("INSERT INTO images VALUES (?, ?, ?, ?, ?, ?, ?)", (full_url, i["alt"], image_url_to_get, "", md5_checksum, caption, ocr_result, ))
					else:
						print("updating {} image as image already indexed".format(image_url_to_get))
						if published_on != None:
							cursor.execute("UPDATE images SET post_url = ?, alt_text = ?, image_src = ?, published = ? WHERE image_src = ?", (full_url, i["alt"], image_url_to_get, published_on["datetime"].split("T")[0], image_url_to_get, ))
						else:
							cursor.execute("UPDATE images SET post_url = ?, alt_text = ?, image_src = ?, published = ? WHERE image_src = ?", (full_url, i["alt"], image_url_to_get, "", image_url_to_get, ))

					images_indexed += 1

			except Exception as e:
				print("error with processing {} image".format(image_url_to_get))
				print(e)
				logging.warning("error with processing {} image".format(image_url_to_get))
				logging.warning(e)

	return images_indexed