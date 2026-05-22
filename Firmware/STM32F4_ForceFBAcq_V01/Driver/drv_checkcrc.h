#ifndef _DRV_CHECKCRC_H_
#define _DRV_CHECKCRC_H_

#include "common.h"


uint8_t BCC_Check(uint8_t * Data,uint8_t Len);

void SetCRCData(unsigned char * pszBuf, uint16_t unLength);
uint16_t GetCRC16(unsigned char * pszBuf, uint16_t unLength);
uint8_t CheckCRC16(unsigned char * pszBuf, uint16_t unLength);

void SetBMS_CRCData(unsigned char * pszBuf, uint16_t unLength);
bool BMSCheckMCRC16(unsigned char * pszBuf, uint16_t unLength);
uint16_t BMSCRC16(uint8_t pszBuf[], uint16_t start, uint16_t unLength);

#endif

