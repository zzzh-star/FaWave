/**
  ******************************************************************************
  * @file    spi.c
  * $Revision: 17 $
  * $Date:: 2014-10-25 11:16:48 +0800 #$
  * @brief   SPI驱动函数实现.
  ******************************************************************************
  * @attention
  *
  *<h3><center>&copy; Copyright 2009-2012, EmbedNet</center>
  *<center><a href="http:\\www.embed-net.com">http://www.embed-net.com</a></center>
  *<center>All Rights Reserved</center></h3>
  *
  ******************************************************************************
  */
/* Includes ------------------------------------------------------------------*/
#include "common.h"
#include "spi.h"
#include "w5500.h"


/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/* Private macro -------------------------------------------------------------*/
/* Private variables ---------------------------------------------------------*/
/* Private function prototypes -----------------------------------------------*/
/* Private functions ---------------------------------------------------------*/

u8 W5500_Interrupt = 0;


void EXTI15_10_IRQHandler(void)
{
  if(EXTI_GetITStatus(EXTI_Line11) != RESET)
  {
    EXTI_ClearITPendingBit(EXTI_Line11);
    W5500_Interrupt = 1;
    //W5500_Interrupt_Process();
  }

//	delay_ms(10);	//消抖
//	if(KEY0==0)
//	{
//		LED0=!LED0;
//		LED1=!LED1;
//	}
//	 EXTI_ClearITPendingBit(EXTI_Line11);//清除LINE4上的中断标志位
}



/**
  * @brief  使能SPI时钟
  * @retval None
  */
static void SPI_RCC_Configuration(void)
{
  RCC_AHB1PeriphClockCmd(RCC_AHB1Periph_GPIOB, ENABLE);
  RCC_APB1PeriphClockCmd(RCC_APB1Periph_SPI2, ENABLE);
  GPIO_PinAFConfig(GPIOB, GPIO_PinSource13,  GPIO_AF_SPI2);
  GPIO_PinAFConfig(GPIOB, GPIO_PinSource14, GPIO_AF_SPI2);
  GPIO_PinAFConfig(GPIOB, GPIO_PinSource15, GPIO_AF_SPI2);
}



/**
  * @brief  配置指定SPI的引脚
  * @retval None
  */
static void SPI_GPIO_Configuration(void)
{
  GPIO_InitTypeDef GPIO_InitStruct;
  EXTI_InitTypeDef  EXTI_InitStructure;

  //PA4->CS,PA5->SCK,PA6->MISO,PA7->MOSI
  GPIO_InitStruct.GPIO_Pin =  GPIO_Pin_13 | GPIO_Pin_14 | GPIO_Pin_15;
  GPIO_InitStruct.GPIO_Speed = GPIO_Speed_100MHz;
  GPIO_InitStruct.GPIO_Mode = GPIO_Mode_AF;
  GPIO_InitStruct.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStruct.GPIO_PuPd  = GPIO_PuPd_DOWN;
  GPIO_Init(GPIOB, &GPIO_InitStruct);

  //初始化复位输出引脚
  GPIO_InitStruct.GPIO_Pin = GPIO_Pin_10;
  GPIO_InitStruct.GPIO_Mode = GPIO_Mode_OUT;
  GPIO_InitStruct.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStruct.GPIO_PuPd = GPIO_PuPd_UP;
  GPIO_Init(GPIOB, &GPIO_InitStruct);
  GPIO_SetBits(GPIOB, GPIO_Pin_10);

  //初始化片选输出引脚
  GPIO_InitStruct.GPIO_Pin = GPIO_Pin_12;
  GPIO_InitStruct.GPIO_Mode = GPIO_Mode_OUT;
  GPIO_InitStruct.GPIO_OType = GPIO_OType_PP;
  GPIO_InitStruct.GPIO_PuPd = GPIO_PuPd_UP;
  GPIO_Init(GPIOB, &GPIO_InitStruct);
  GPIO_SetBits(GPIOB, GPIO_Pin_12);

  /* W5500_INT引脚初始化配置(PB11) */
  GPIO_InitStruct.GPIO_Pin = W5500_INT;
  GPIO_InitStruct.GPIO_Speed = GPIO_Speed_50MHz;
  GPIO_InitStruct.GPIO_Mode = GPIO_Mode_IN;
  GPIO_InitStruct.GPIO_PuPd = GPIO_PuPd_UP;//
  GPIO_Init(W5500_INT_PORT, &GPIO_InitStruct);
  GPIO_SetBits(W5500_INT_PORT, W5500_INT);

  RCC_APB2PeriphClockCmd(RCC_APB2Periph_SYSCFG, ENABLE);//使能SYSCFG时钟
  SYSCFG_EXTILineConfig(EXTI_PortSourceGPIOB, EXTI_PinSource11);

  /* PB11 as W5500 interrupt input */
  EXTI_InitStructure.EXTI_Line = EXTI_Line11;
  EXTI_InitStructure.EXTI_Mode = EXTI_Mode_Interrupt;
  EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Falling;
  EXTI_InitStructure.EXTI_LineCmd = ENABLE;
  EXTI_Init(&EXTI_InitStructure);

  NVIC_InitTypeDef   NVIC_InitStructure;
  NVIC_InitStructure.NVIC_IRQChannel = EXTI15_10_IRQn;//外部中断0
  NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 0x00;//抢占优先级0
  NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0x02;//子优先级2
  NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;//使能外部中断通道
  NVIC_Init(&NVIC_InitStructure);//配置

}
/**
  * @brief  根据外部SPI设备配置SPI相关参数
  * @retval None
  */
void SPI_Configuration(void)
{
  SPI_InitTypeDef SPI_InitStruct;

  SPI_RCC_Configuration();
  SPI_GPIO_Configuration();

  SPI_InitStruct.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_2;
  SPI_InitStruct.SPI_Direction = SPI_Direction_2Lines_FullDuplex;
  SPI_InitStruct.SPI_Mode = SPI_Mode_Master;
  SPI_InitStruct.SPI_DataSize = SPI_DataSize_8b;
  SPI_InitStruct.SPI_CPOL = SPI_CPOL_Low;
  SPI_InitStruct.SPI_CPHA = SPI_CPHA_1Edge;
  SPI_InitStruct.SPI_NSS = SPI_NSS_Soft;
  SPI_InitStruct.SPI_FirstBit = SPI_FirstBit_MSB;
  SPI_InitStruct.SPI_CRCPolynomial = 7;
  SPI_Init(SPI2, &SPI_InitStruct);

  SPI_Cmd(SPI2, ENABLE);
}
/**
  * @brief  写1字节数据到SPI总线
  * @param  TxData 写到总线的数据
  * @retval None
  */
void SPI_WriteByte(uint8_t TxData)
{
  while((SPI2->SR & SPI_I2S_FLAG_TXE) == 0);	//等待发送区空

  SPI2->DR = TxData;	 	  									//发送一个byte

  while((SPI2->SR & SPI_I2S_FLAG_RXNE) == 0); //等待接收完一个byte

  SPI2->DR;
}
/**
  * @brief  从SPI总线读取1字节数据
  * @retval 读到的数据
  */
uint8_t SPI_ReadByte(void)
{
  while((SPI2->SR & SPI_I2S_FLAG_TXE) == 0);	//等待发送区空

  SPI2->DR = 0xFF;	 	  										//发送一个空数据产生输入数据的时钟

  while((SPI2->SR & SPI_I2S_FLAG_RXNE) == 0); //等待接收完一个byte

  return SPI2->DR;
}
/**
  * @brief  进入临界区
  * @retval None
  */
void SPI_CrisEnter(void)
{
  __set_PRIMASK(1);
}
/**
  * @brief  退出临界区
  * @retval None
  */
void SPI_CrisExit(void)
{
  __set_PRIMASK(0);
}

/**
  * @brief  片选信号输出低电平
  * @retval None
  */
void SPI_CS_Select(void)
{
  GPIO_ResetBits(GPIOB, GPIO_Pin_12);
}
/**
  * @brief  片选信号输出高电平
  * @retval None
  */
void SPI_CS_Deselect(void)
{
  GPIO_SetBits(GPIOB, GPIO_Pin_12);
}
/*********************************END OF FILE**********************************/

