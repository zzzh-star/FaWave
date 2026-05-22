#include "drv_ads1251.h"

#define VOL_ALPHA     0.1f

ADS1251Msg  gAD1_Data;
ADS1251Msg  gAD2_Data;
ADS1251Msg  gAD3_Data;
ADS1251Msg  gAD4_Data;
float volData[4]      = {0};
float volData_Last[4] = {0};

void adsDataInit(void)
{
	memset(&gAD1_Data, 0,sizeof(gAD1_Data)); //通道1
	memset(&gAD2_Data, 0,sizeof(gAD2_Data)); //通道2
	memset(&gAD3_Data, 0,sizeof(gAD3_Data)); //通道3
	memset(&gAD4_Data, 0,sizeof(gAD4_Data)); //通道4
}	
void ADS1251_GPIOInit(void)
{
	GPIO_InitTypeDef GPIO_InitStructure;

  RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOA , ENABLE); 
	RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOB , ENABLE); 
	RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOC, ENABLE); 
	RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOD, ENABLE); 
	
  GPIO_InitStructure.GPIO_Pin = GPIO_Pin_8|GPIO_Pin_11;		// ADS1251_CLK
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
  GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_100MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOA, &GPIO_InitStructure);

  GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6|GPIO_Pin_8;		//ADS1251_CLK
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
  GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_100MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOC, &GPIO_InitStructure);
	
  GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14;		//ADS1251_CLK
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_OUT;
  GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_100MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOD, &GPIO_InitStructure);


	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_7|GPIO_Pin_9 ;		//ADS1251_Data
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOC, &GPIO_InitStructure);
	
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_15 ;		//ADS1251_Data
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOD, &GPIO_InitStructure);
	
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;		//ADS1251_Data
  GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOA, &GPIO_InitStructure);
	
	ADS1_SCLK(0);
	ADS2_SCLK(0);
	ADS3_SCLK(0);
	ADS4_SCLK(0);
	adsDataInit();
}
/*********************************************************
** 定时器初始化
*********************************************************/
void TIM2_Config(uint16_t arr, uint16_t psc)
{
  TIM_TimeBaseInitTypeDef TIM_TimeBaseInitStructure;
  NVIC_InitTypeDef NVIC_InitStructure;

  RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);

  TIM_TimeBaseInitStructure.TIM_Period    = arr; 	                //自动重装载值
  TIM_TimeBaseInitStructure.TIM_Prescaler = psc;                  //定时器分频
  TIM_TimeBaseInitStructure.TIM_CounterMode = TIM_CounterMode_Up; //向上计数模式
  TIM_TimeBaseInitStructure.TIM_ClockDivision = TIM_CKD_DIV1;

  TIM_TimeBaseInit(TIM2, &TIM_TimeBaseInitStructure); 

  TIM_ITConfig(TIM2, TIM_IT_Update, ENABLE);                      //允许定时器2更新中断
  TIM_Cmd(TIM2, ENABLE); 

  NVIC_InitStructure.NVIC_IRQChannel = TIM2_IRQn;             
  NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x01;    //抢占优先级1
  NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0x02;           //子优先级3
  NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
  NVIC_Init(&NVIC_InitStructure);
}
/*****************************************************
**  ADS1251 数据获取
*****************************************************/
void ADS1_GetData(void)
{
	switch(gAD1_Data.adState)
	{
		case 0:  if(gAD1_Data.oldData && !ADS1_DATA)
							{
								gAD1_Data.adState = 10;
								gAD1_Data.adFinishFlg = 1;
							}
							gAD1_Data.oldData = ADS1_DATA;
							break;

		case 10:  gAD1_Data.adTime++;
							if(gAD1_Data.adTime > 50)
							{
								gAD1_Data.adTime = 0;
								gAD1_Data.adState = 30;
								gAD1_Data.adSeq = 0;
								gAD1_Data.adSval = 0;
							}
							break;

		case 30:  ADS1_SCLK(1);
							gAD1_Data.adState = 40;
							break;

		case 40:  if(ADS1_DATA)
								gAD1_Data.adSval |= 0x01;

							gAD1_Data.adSval <<= 1;
							ADS1_SCLK(0);
							gAD1_Data.adState = 30;
							gAD1_Data.adSeq++;

							if(gAD1_Data.adSeq >= 23)
							{
								gAD1_Data.adState    = 0;
								gAD1_Data.getAdVal   = gAD1_Data.adSval;
								gAD1_Data.showAdsVal = (gAD1_Data.getAdVal >> 8);
							}

			break;
	}
}
/*****************************************************
**  ADS1251 数据获取
*****************************************************/
void ADS2_GetData(void)
{
	switch(gAD2_Data.adState)
	{
		case 0:  if(gAD2_Data.oldData && !ADS2_DATA)
							{
								gAD2_Data.adState = 10;
								gAD2_Data.adFinishFlg = 1;
							}
							gAD2_Data.oldData = ADS2_DATA;
							break;

		case 10:  gAD2_Data.adTime++;
							if(gAD2_Data.adTime > 50)
							{
								gAD2_Data.adTime = 0;
								gAD2_Data.adState = 30;
								gAD2_Data.adSeq = 0;
								gAD2_Data.adSval = 0;
							}
							break;

		case 30:  ADS2_SCLK(1);
							gAD2_Data.adState = 40;
							break;

		case 40:  if(ADS2_DATA)
								gAD2_Data.adSval |= 0x01;

							gAD2_Data.adSval <<= 1;
							ADS2_SCLK(0);
							gAD2_Data.adState = 30;
							gAD2_Data.adSeq++;

							if(gAD2_Data.adSeq >= 23)
							{
								gAD2_Data.adState = 0;
								gAD2_Data.getAdVal = gAD2_Data.adSval;
								gAD2_Data.showAdsVal = (gAD2_Data.getAdVal >> 8);
							}
			break;
	}
}
/***************************************************************
**  ADS1251 数据获取
***************************************************************/
void ADS3_GetData(void)
{
	switch(gAD3_Data.adState)
	{
		case 0:  if(gAD3_Data.oldData && !ADS3_DATA)
							{
								gAD3_Data.adState = 10;
								gAD3_Data.adFinishFlg = 1;
							}
							gAD3_Data.oldData = ADS3_DATA;
							break;

		case 10:  gAD3_Data.adTime++;
							if(gAD3_Data.adTime > 50)
							{
								gAD3_Data.adTime = 0;
								gAD3_Data.adState = 30;
								gAD3_Data.adSeq = 0;
								gAD3_Data.adSval = 0;
							}
							break;

		case 30:  ADS3_SCLK(1);
							gAD3_Data.adState = 40;
							break;

		case 40:  if(ADS3_DATA) 
								gAD3_Data.adSval |= 0x01;

							gAD3_Data.adSval <<= 1;
							ADS3_SCLK(0);
							gAD3_Data.adState = 30;
							gAD3_Data.adSeq++;

							if(gAD3_Data.adSeq >= 23)
							{
								gAD3_Data.adState    =  0;
								gAD3_Data.getAdVal   =  gAD3_Data.adSval;
								gAD3_Data.showAdsVal = (gAD3_Data.getAdVal >> 8);
							}
			break;
	}
}
/***************************************************************
**  ADS1251 数据获取
***************************************************************/
void ADS4_GetData(void)
{
	switch(gAD4_Data.adState)
	{
		case 0:  if(gAD4_Data.oldData && !ADS3_DATA)
							{
								gAD4_Data.adState = 10;
								gAD4_Data.adFinishFlg = 1;
							}
							gAD4_Data.oldData = ADS3_DATA;
							break;

		case 10:  gAD4_Data.adTime++;
							if(gAD4_Data.adTime > 50)
							{
								gAD4_Data.adTime = 0;
								gAD4_Data.adState = 30;
								gAD4_Data.adSeq = 0;
								gAD4_Data.adSval = 0;
							}
							break;

		case 30:  ADS4_SCLK(1);
							gAD4_Data.adState = 40;
							break;

		case 40:  if(ADS4_DATA) 
								gAD4_Data.adSval |= 0x01;

							gAD4_Data.adSval <<= 1;
							ADS4_SCLK(0);
							gAD4_Data.adState = 30;
							gAD4_Data.adSeq++;

							if(gAD4_Data.adSeq >= 23)
							{
								gAD4_Data.adState    =  0;
								gAD4_Data.getAdVal   =  gAD4_Data.adSval;
								gAD4_Data.showAdsVal = (gAD4_Data.getAdVal >> 8);
							}
			break;
	}
}
/********************************************************
** ADS1251 数据获取  
********************************************************/
void ADS_GetValue(void)
{
	  gAD1_Data.AD_CLK_Flg = !gAD1_Data.AD_CLK_Flg;
    ADS1251_CLK(gAD1_Data.AD_CLK_Flg);
	
    if(gAD1_Data.AD_CLK_Flg)
    {
      ADS2_GetData();
      ADS3_GetData();
      ADS1_GetData();
			ADS4_GetData();
    }
		getVoltage();
}


float ema_filter(float new_val, float old_val) 
{
  return VOL_ALPHA * new_val + (1.0f - VOL_ALPHA) * old_val;
}

void getVoltage(void)
{
	volData[0] = (gAD1_Data.showAdsVal*5.0f)* 1.0f/32768.0f ;  //原始电压 = 通道数据 * 参考电压 / AD分辨率 / 放大倍倍数  * 1000      单位mv
	volData[1] = (gAD2_Data.showAdsVal*5.0f)* 1.0f/32768.0f ;
	volData[2] = (gAD3_Data.showAdsVal*5.0f)* 1.0f/32768.0f ;
	volData[3] = (gAD4_Data.showAdsVal*5.0f)* 1.0f/32768.0f ;
	
	for(uint8_t i=0;i<4;i++)
	{
		volData[i] = ema_filter(volData[i],volData_Last[i]);
	}
	
	memcpy(volData_Last,volData,16);
}


/************************************************************
** 中断初始化
************************************************************/
void TIM2_IRQHandler(void)
{
  if(TIM_GetITStatus(TIM2, TIM_IT_Update) == SET) //溢出中断
  {
		ADS_GetValue();
		TIM_ClearITPendingBit(TIM2, TIM_IT_Update); //清除中断标志位
  }
}
