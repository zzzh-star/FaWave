#ifndef _DRV_ADS12551_H_
#define _DRV_ADS12551_H_

#include "common.h"
  
#define ADS1251_CLK(x)   x  ?   GPIO_SetBits(GPIOA,GPIO_Pin_11)  : GPIO_ResetBits(GPIOA,GPIO_Pin_11)

#define ADS1_DATA        GPIO_ReadInputDataBit(GPIOD, GPIO_Pin_15)
#define ADS1_SCLK(x)     x  ?   GPIO_SetBits(GPIOD,GPIO_Pin_14) : GPIO_ResetBits(GPIOD,GPIO_Pin_14)

#define ADS2_DATA        GPIO_ReadInputDataBit(GPIOC, GPIO_Pin_7)
#define ADS2_SCLK(x)     x  ?   GPIO_SetBits(GPIOC,GPIO_Pin_6)  : GPIO_ResetBits(GPIOC,GPIO_Pin_6)

#define ADS3_DATA        GPIO_ReadInputDataBit(GPIOC, GPIO_Pin_9)
#define ADS3_SCLK(x)     x  ?   GPIO_SetBits(GPIOC,GPIO_Pin_8)  : GPIO_ResetBits(GPIOC,GPIO_Pin_8)

#define ADS4_DATA        GPIO_ReadInputDataBit(GPIOA, GPIO_Pin_9)
#define ADS4_SCLK(x)     x  ?   GPIO_SetBits(GPIOA,GPIO_Pin_8)  : GPIO_ResetBits(GPIOA,GPIO_Pin_8)




typedef struct
{
	uint8_t   adState;
	uint8_t   adTime;
	uint8_t   adSeq;
	uint32_t  adSval;
	uint32_t  getAdVal;
	uint8_t   oldData;
	short     showAdsVal;
	uint8_t   adFinishFlg;
	uint8_t   AD_CLK_Flg;

}ADS1251Msg;

extern  float       volData[];
extern  ADS1251Msg  gAD1_Data;
extern  ADS1251Msg  gAD2_Data;
extern  ADS1251Msg  gAD3_Data;
extern  ADS1251Msg  gAD4_Data;

void getVoltage(void);
void ADS_GetValue(void); 
void adsDataInit(void);
void ADS1251_GPIOInit(void);
void TIM2_Config(uint16_t arr, uint16_t psc);

#endif 


