#include "drv_checkcrc.h"
/***********************************************
** 
***********************************************/
uint8_t BCC_Check(uint8_t * Data,uint8_t Len)
{
	uint8_t Res = 0;
	for(uint8_t i = 0;i < Len; i++)
	{
		Res += *(Data+i);
	}
	return Res;
}
uint16_t GetCRC16(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t i, j, CurVal;
  uint16_t CrcReg = 0xFFFF;

  for (i = 0; i < unLength; i++)
  {
    CurVal = pszBuf[i] << 8;

    for (j = 0; j < 8; j++)
    {
      if ((short)(CrcReg ^ CurVal) < 0)
        CrcReg = (CrcReg << 1) ^ 0x1021;
      else
        CrcReg <<= 1;

      CurVal <<= 1;
    }
  }
  return CrcReg;
}
void SetCRCData(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t ret = GetCRC16(pszBuf, unLength);
  pszBuf[unLength] = ret & 0xff;
  pszBuf[unLength + 1] = (ret >> 8);
}
uint8_t CheckCRC16(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t Result = GetCRC16(pszBuf, unLength);
  if((Result & 0xff) == pszBuf[unLength] && (Result >> 8) == pszBuf[unLength + 1])
  {
    return 1;
  }
  return 0;
}


/***********************************************
** ???
***********************************************/
uint16_t CRC16(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t i, j, CurVal;
  uint16_t CrcReg = 0xFFFF;

  for (i = 0; i < unLength; i++)
  {
    CurVal = pszBuf[i] << 8;

    for (j = 0; j < 8; j++)
    {
      if ((short)(CrcReg ^ CurVal) < 0)
        CrcReg = (CrcReg << 1) ^ 0x1021;
      else
        CrcReg <<= 1;

      CurVal <<= 1;
    }
  }

  return CrcReg;
}
/************************************************************************
** 
************************************************************************/
uint16_t BMSCRC16(uint8_t pszBuf[], uint16_t start, uint16_t unLength)
{
  uint16_t i, j, CurVal;
  uint16_t CrcReg = 0xFFFF;
  CurVal = CrcReg;

  for (i = 0; i < unLength; i++)
  {
    CrcReg = (uint16_t)(pszBuf[start + i] ^ CrcReg);

    for (j = 0; j < 8; j++)
    {
      CurVal = CrcReg;
      CrcReg >>= 1;

      if ((short)(CurVal & 0x0001) == 0x0001)
        CrcReg = (uint16_t)(CrcReg  ^ (uint16_t)(0xa001));
    }
  }
  return CrcReg;
}
void SetBMS_CRCData(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t ret = BMSCRC16(pszBuf, 0, unLength);
  pszBuf[unLength] = ret & 0xff;
  pszBuf[unLength + 1] = (ret >> 8);
}

bool BMSCheckMCRC16(unsigned char * pszBuf, uint16_t unLength)
{
  uint16_t ret = BMSCRC16(pszBuf, 0, unLength);

  if((ret & 0xff) == pszBuf[unLength] && (ret >> 8) == pszBuf[unLength + 1])
  {
    return true;
  }
  return false;
}


