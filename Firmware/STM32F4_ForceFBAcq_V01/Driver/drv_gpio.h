#ifndef _DRV_GPIO_H_
#define _DRV_GPIO_H_

#include "common.h"
 
#define W5500POWER(x)     x  ?   GPIO_SetBits(GPIOD,GPIO_Pin_13) : GPIO_ResetBits(GPIOD,GPIO_Pin_13)  // W5500供电控制 低电平开
#define DEBUGLED(x)       x  ?   GPIO_SetBits(GPIOD,GPIO_Pin_12) : GPIO_ResetBits(GPIOD,GPIO_Pin_12)  // LED显示  低电平亮

void GPIO_OutInit(void);

#endif 


