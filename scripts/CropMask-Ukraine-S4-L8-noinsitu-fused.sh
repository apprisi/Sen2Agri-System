#!/bin/bash

source set_build_folder.sh

set -e

FILES=( \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130206_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130206_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130226_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130226_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130318_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130318_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130402_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130402_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130412_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130412_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130417_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130417_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130422_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130422_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130427_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130427_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130502_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130502_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130507_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130507_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130512_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130512_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130517_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130517_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130527_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130527_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130601_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130601_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130606_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130606_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130611_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130611_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Spot4-T5/Ukraine/SPOT4_HRVIR1_XS_20130616_N2A_EUkraineD0000B0000/SPOT4_HRVIR1_XS_20130616_N2A_EUkraineD0000B0000.xml \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130416_L8_181_025/EUkraineS2A_20130416_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130502_L8_181_025/EUkraineS2A_20130502_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130518_L8_181_025/EUkraineS2A_20130518_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130603_L8_181_025/EUkraineS2A_20130603_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130619_L8_181_025/EUkraineS2A_20130619_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130705_L8_181_025/EUkraineS2A_20130705_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130721_L8_181_025/EUkraineS2A_20130721_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130806_L8_181_025/EUkraineS2A_20130806_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20130822_L8_181_025/EUkraineS2A_20130822_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20131110_L8_181_025/EUkraineS2A_20131110_L8_181_025.HDR \
    /mnt/Sen2Agri_DataSets/L2A/Landsat8/Ukraine/MACCS_Manual_Format/EUkraineS2A_20131228_L8_181_025/EUkraineS2A_20131228_L8_181_025.HDR \
)

    # -strata ~/areas.shp \
    #/mnt/archive/reference_data/ESACCI-LC-L4-LCCS-Map-300m-P5Y-2010-v1.6.1.tif
./CropMaskFused.py \
    -refr /mnt/data/reference/Reference_Ukraine.tif \
    -input ${FILES[@]} \
    -rseed 0 -pixsize 20 \
    -outdir /mnt/data/ukraine/Ukraine-mask-noinsitu \
    -buildfolder "$BUILD_FOLDER" # -keepfiles
