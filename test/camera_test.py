import awscam
import cv2

def resize_to_width(image, width):
    h, w, _ = image.shape
    new_h = h * width / w
    return cv2.resize(image, (width, new_h))

if __name__ == '__main__':
    while True:
        ret, hi = awscam.getLastFrame()
        if not ret:
            print('Fetching image failed')
            break
        print('Original Resolution: %s' % str(hi.shape))
        hi = resize_to_width(hi, 480)
        cv2.imshow("hi", hi)
        cv2.waitKey(1)
    