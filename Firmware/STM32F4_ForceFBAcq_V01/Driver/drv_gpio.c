#include "drv_gpio.h"

uint8_t gUserLEDflag = 0;

/******************************************************************************
** GPIO 输出初始化
******************************************************************************/
void GPIO_OutInit(void)
{
  GPIO_InitTypeDef  GPIO_InitStructure;
	RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOD , ENABLE); 
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_SYSCFG, ENABLE);//使能SYSCFG时钟
	
  //W5500电源控制  低电平上电  
  GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_13|GPIO_Pin_12;		
  GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_OUT;
  GPIO_InitStructure.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
  GPIO_InitStructure.GPIO_PuPd = GPIO_PuPd_NOPULL;
  GPIO_Init(GPIOD, &GPIO_InitStructure);
  W5500POWER(0);
}

