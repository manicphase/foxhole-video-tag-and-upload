#!/usr/bin/env python
# coding: utf-8

# In[1]:


import random
import cv2
import numpy as np
import inspect
from Levenshtein import distance
from matplotlib import pyplot as plt
import pytesseract
import time


# In[2]:


def encode_booleans(bool_lst):
    res = 0
    for i, bval in enumerate(bool_lst):
        res += int(bval) << i
    return res

def decode_booleans(intval):
    res = []
    for bit in range(8):
        mask = 1 << bit
        res.append((intval & mask) == mask)
    return res

def flip_random_bit(input):
    bits = decode_booleans(input)
    bit_to_change = random.randint(0,7)
    print(f'changing bit {bit_to_change}')
    bits[bit_to_change] = not bits[bit_to_change]
    return encode_booleans(bits)
    
flip_random_bit(250)


# In[3]:


ranks = open("ranks.txt", "r").read().split("\n")
ranks = [r.lower() for r in ranks]

def clean_player_name(input):
    clean_name = input.split("]")[-1].split("(")[0].strip()
    if len(clean_name) > 3: #TODO: find out foxhole rules for valid names to reject more OCR junk
        return clean_name
    return None

def scrape_names(img):
    valid_names = []
    psm=11
    try:
        #print(f'using psm {psm}')
        print("b4 tess")
        text = pytesseract.image_to_string(img, config =f'--psm {psm}')
        print("after tess")
        #print(text)
        names = [n for n in text.split("\n") if n.endswith(")")]
        for r in ranks:
            for n in names:
                if n.lower().endswith(f'({r.lower()})'):
                    valid_names.append(n)

    except:
        pass
    return valid_names

def clean_player_name(input):
    clean_name = input.split("]")[-1].split("(")[0].strip()
    if len(clean_name) > 3: #TODO: find out foxhole rules for valid names to reject more OCR junk
        return clean_name
    return None

def get_clean_player_names(names):
    clean_names = []
    for name in names:
        new_name = clean_player_name(name)
        if new_name:
            clean_names.append(new_name)
    return clean_names


# In[4]:


#signature = inspect.signature(increase_contrast)


# In[5]:


#signature


# In[6]:


#p = list(signature.parameters.values())[2]


# In[7]:


#p.name


# In[8]:


names = ["Hardcore", "Super Franky 62", "awm_roll", "TOSO", "Reboot", "Elikmyr", 
         "GeneralEren", "Voltair", "Sike", "ubermensch", "ssSmoozy", "JuhnWeak",
         "Voltair", "Pickweek", "Clint", "LoneNoodle", "Whisqey", "Raskim",
         "h4med", "naza07", "ThursdayAfternoon", "Sacondez", "Giraffenboi",
         "Proper Gun Fight"]


# In[9]:


scores = [distance("Clint", name) for name in names]
scores.sort()
scores[0]

def score_results(target, results):
    total_score = 0
    for name in target:
        all_scores = [distance(name, guess) for guess in results]
        all_scores.sort()
        if all_scores:
            total_score += all_scores[0]
    return total_score


# In[10]:


def increase_contrast(img, mask, clipLimit=2.0, tileGridSizeX=8, tileGridSizeY=8):
    clipLimit = clipLimit / 10.0
    # converting to LAB color space
    lab= cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    
    # Applying CLAHE to L-channel
    # feel free to try different values for the limit and grid size:
    clahe = cv2.createCLAHE(clipLimit=clipLimit, tileGridSize=(tileGridSizeX+1,tileGridSizeY+1))
    cl = clahe.apply(l_channel)
    
    # merge the CLAHE enhanced L-channel with the a and b channel
    limg = cv2.merge((cl,a,b))
    
    # Converting image from LAB Color model to BGR color spcae
    enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # Stacking the original image with the enhanced image
    result = np.hstack((img, enhanced_img))
       
    #plt.imshow(enhanced_img)
    #plt.title('my picture')
    #plt.show()
    return enhanced_img

img = cv2.imread("manynames.png",1)
def show(img):
    plt.imshow(img)
    plt.show()

#show(img)


# In[ ]:


print(get_clean_player_names(scrape_names(img)))

first_run = [1,1,1]

def do_run(run_deets):
    result = get_clean_player_names(scrape_names(increase_contrast(img,img,*run_deets)))
    print(result)
    print(score_results(names, result))

do_run(first_run)
for x in range(10):
    new_run = [flip_random_bit(i) for i in first_run]
    print(new_run)
    do_run(new_run)
    time.sleep(1)


increase_contrast(img,img,200)
increase_contrast(img,img,100)
increase_contrast(img,img,0)
increase_contrast(img,img,50,100,100)


# In[ ]:


increase_contrast(img,img,50)


# In[ ]:




