import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
import cv2
import pickle

# load calibration parameters
calibration = pickle.load(open("camera_calibration.p", "rb"))
mtx = calibration['mtx']
dist = calibration['dist']
init = True
left_fit_glob = []
right_fit_glob = []
ploty_glob = []

def undistort(image):
	dst_image = cv2.undistort(image, mtx, dist, None, mtx)
	return(dst_image)

def threshold_combine(image):
	# HLS features
	hls = cv2.cvtColor(image, cv2.COLOR_RGB2HLS)
	s_channel = hls[:,:,2]

	gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
	# Sobel x
	sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0) # Take the derivative in x
	abs_sobelx = np.absolute(sobelx) # Absolute x derivative to accentuate lines away from horizontal
	scaled_sobel = np.uint8(255*abs_sobelx/np.max(abs_sobelx))

	# Threshold x gradient
	thresh_min = 20
	thresh_max = 100
	sxbinary = np.zeros_like(scaled_sobel)
	sxbinary[(scaled_sobel >= thresh_min) & (scaled_sobel <= thresh_max)] = 1

	# Threshold color HLS
	s_thresh_min = 150
	s_thresh_max = 255
	s_binary = np.zeros_like(s_channel)
	s_binary[(s_channel >= s_thresh_min) & (s_channel <= s_thresh_max)] = 1

	# Combine the two binary thresholds
	combined_binary = np.zeros_like(sxbinary)
	combined_binary[(s_binary == 1) | (sxbinary == 1)] = 1
	return combined_binary

def perspective_transform(image, img_size, mode='src_dst'):

	# Source points
	src = np.float32([ #x , y. y=0 is at most top, x = 0 is at most left
		[830, 525], #top right
		[1080, 670], #bot right
		[340, 670], #bot left
		[510, 525]]) #top left

	# Destination points, X destination is taken as mid value of src X top and bot
	dst = np.float32([
		[960, 525], 
		[960, 670],
		[400, 670],
		[400, 525]])

	# Given src and dst points, calculate the perspective transform matrix
	M = cv2.getPerspectiveTransform(src, dst)
	Minv = cv2.getPerspectiveTransform(dst, src)

	if (mode=='src_dst'):
		transform_mat = M
	else:
		transform_mat = Minv

	# Warp the image using OpenCV warpPerspective()
	warped = cv2.warpPerspective(image, transform_mat, img_size, flags=cv2.INTER_LINEAR)
	return warped

def find_line_new(image, y_start=475, x_start=100, x_end=1180):
	# Take a histogram of the part specified of the image
	histogram = np.sum(image[y_start:,:], axis=0)
	# Create an output image to draw on
	out_img = np.dstack((image, image, image))*255
	# Find the peak of the left and right halves of the histogram
	# These will be the starting point for the left and right lines
	midpoint = np.int(histogram.shape[0]/2)
	leftx_base = np.argmax(histogram[:midpoint])
	rightx_base = np.argmax(histogram[midpoint:]) + midpoint

	# Choose the number of sliding windows
	nwindows = 9
	# Set height of windows
	window_height = np.int(image.shape[0]/nwindows)
	# Identify the x and y positions of all nonzero pixels in the image
	nonzero = image.nonzero()
	nonzeroy = np.array(nonzero[0])
	nonzerox = np.array(nonzero[1])
	# Current positions to be updated for each window
	leftx_current = leftx_base
	rightx_current = rightx_base
	# Set the width of the windows +/- margin
	margin = 100
	# Set minimum number of pixels found to recenter window
	minpix = 50
	# Create empty lists to receive left and right lane pixel indices
	left_lane_inds = []
	right_lane_inds = []

	# Step through the windows one by one
	for window in range(nwindows):
	    # Identify window boundaries in x and y (and right and left)
	    win_y_low = image.shape[0] - (window+1)*window_height
	    win_y_high = image.shape[0] - window*window_height
	    win_xleft_low = leftx_current - margin
	    win_xleft_high = leftx_current + margin
	    win_xright_low = rightx_current - margin
	    win_xright_high = rightx_current + margin
	    # Draw the windows on the visualization image
	    cv2.rectangle(out_img,(win_xleft_low,win_y_low),(win_xleft_high,win_y_high),(0,255,0), 2) 
	    cv2.rectangle(out_img,(win_xright_low,win_y_low),(win_xright_high,win_y_high),(0,255,0), 2) 
	    # Identify the nonzero pixels in x and y within the window
	    good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
	    good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]
	    # Append these indices to the lists
	    left_lane_inds.append(good_left_inds)
	    right_lane_inds.append(good_right_inds)
	    # If you found > minpix pixels, recenter next window on their mean position
	    if len(good_left_inds) > minpix:
	        leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
	    if len(good_right_inds) > minpix:        
	        rightx_current = np.int(np.mean(nonzerox[good_right_inds]))

	# Concatenate the arrays of indices
	left_lane_inds = np.concatenate(left_lane_inds)
	right_lane_inds = np.concatenate(right_lane_inds)

	# Extract left and right line pixel positions
	leftx = nonzerox[left_lane_inds]
	lefty = nonzeroy[left_lane_inds] 
	rightx = nonzerox[right_lane_inds]
	righty = nonzeroy[right_lane_inds] 

	# Fit a second order polynomial to each
	left_fit = np.polyfit(lefty, leftx, 2)
	right_fit = np.polyfit(righty, rightx, 2)   

	# Generate x and y values for plotting
	ploty = np.linspace(0, image.shape[0]-1, image.shape[0] )
	left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
	right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]
	return ploty, left_fitx, right_fitx, left_fit, right_fit

def find_line(image, left_fit, right_fit, y_start = 400):
	""" find line base on previous finding """
	nonzero = image.nonzero()
	nonzeroy = np.array(nonzero[0])
	nonzerox = np.array(nonzero[1])
	margin = 50
	left_lane_inds = ((nonzerox > (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] - margin)) & (nonzerox < (left_fit[0]*(nonzeroy**2) + left_fit[1]*nonzeroy + left_fit[2] + margin))) 
	right_lane_inds = ((nonzerox > (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] - margin)) & (nonzerox < (right_fit[0]*(nonzeroy**2) + right_fit[1]*nonzeroy + right_fit[2] + margin)))  

	leftx = nonzerox[left_lane_inds]
	lefty = nonzeroy[left_lane_inds] 
	rightx = nonzerox[right_lane_inds]
	righty = nonzeroy[right_lane_inds]
	# Fit a second order polynomial to each
	left_fit = np.polyfit(lefty, leftx, 2)
	right_fit = np.polyfit(righty, rightx, 2)
	# Generate x and y values for plotting
	ploty = np.linspace(0, image.shape[0]-1, image.shape[0] )
	left_fitx = left_fit[0]*ploty**2 + left_fit[1]*ploty + left_fit[2]
	right_fitx = right_fit[0]*ploty**2 + right_fit[1]*ploty + right_fit[2]
	return ploty, left_fitx, right_fitx, left_fit, right_fit

def sanity_check(ploty, left_fit, right_fit):
	""" give the line distance """
	# Define conversions in x and y from pixels space to meters
	ym_per_pix = 30/720 # meters per pixel in y dimension
	xm_per_pix = 3.7/700 # meters per pixel in x dimension
	#bottom of image
	y_max = np.max(ploty)
	y_min = np.min(ploty)

	x_left_max = left_fit[0]*(y_max**2) + left_fit[1]*y_max + left_fit[2]
	x_right_max = right_fit[0]*(y_max**2) + right_fit[1]*y_max + right_fit[2]

	x_left_min = left_fit[0]*(y_min**2) + left_fit[1]*y_min + left_fit[2]
	x_right_min = right_fit[0]*(y_min**2) + right_fit[1]*y_min + right_fit[2]

	distance_max = x_right_max - x_left_max
	distance_max_meter = distance_max * xm_per_pix

	distance_min = x_right_min - x_left_min
	distance_min_meter = distance_min * xm_per_pix
	return distance_max_meter, distance_min_meter


def process_image(image):
	global init
	global left_fit_glob
	global right_fit_glob
	global ploty_glob

	undistorted_img = undistort(image)
	combined_binary = threshold_combine(undistorted_img)

	img_size = (image.shape[1], image.shape[0])
	warped_img = perspective_transform(combined_binary, img_size, mode="src_dst")
	# distance between lines on the bottom of image
	distance = 0
	# distance between lines on the top part of the line
	distance_min = 0
	#this is the start of video
	if (init == True):
		ploty, left_fitx, right_fitx, left_fit, right_fit = find_line_new(warped_img, y_start=400)
		left_fit_glob = left_fit
		right_fit_glob = right_fit
		ploty_glob = ploty
		init = False
	else:
		ploty, left_fitx, right_fitx, left_fit, right_fit = find_line(warped_img, left_fit_glob, right_fit_glob, y_start=400)
		distance, distance_min = sanity_check(warped_img, left_fit, right_fit)
		# if line distance is outside this range, find using window sliding
		if (distance > 2 and distance < 3.2) and (distance_min > 2 and distance_min < 3.2):
			left_fit_glob = left_fit
			right_fit_glob = right_fit
			ploty_glob = ploty
		else:
			ploty, left_fitx, right_fitx, left_fit, right_fit = find_line_new(warped_img, y_start=400)
			left_fit_glob = left_fit
			right_fit_glob = right_fit
			ploty_glob = ploty

	# Create an image to draw the lines on
	warp_zero = np.zeros_like(warped_img).astype(np.uint8)
	color_warp = np.dstack((warp_zero, warp_zero, warp_zero))

	# Recast the x and y points into usable format for cv2.fillPoly()
	pts_left = np.array([np.transpose(np.vstack([left_fitx, ploty]))])
	pts_right = np.array([np.flipud(np.transpose(np.vstack([right_fitx, ploty])))])
	pts = np.hstack((pts_left, pts_right))

	# Draw the lane onto the warped blank image
	cv2.fillPoly(color_warp, np.int_([pts]), (0,255, 0))

	# Warp the blank back to original image space using inverse perspective matrix (Minv)
	newwarp = perspective_transform(color_warp, img_size, mode="dst_src")
	# Combine the result with the original image
	result = cv2.addWeighted(undistorted_img, 1, newwarp, 0.3, 0)
	return result