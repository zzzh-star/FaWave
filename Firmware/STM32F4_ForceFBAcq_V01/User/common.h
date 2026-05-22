#ifndef  __COMMON_H_
#define  __COMMON_H_

#define INLINE  __inline

#include "misc.h"
#include "math.h"
#include "string.h"
#include "stdlib.h"
#include "stdio.h"
#include <stdbool.h>

#include "stm32f4xx.h"
#include "stm32f4xx_adc.h"
#include "stm32f4xx_spi.h"
#include "stm32f4xx_can.h"
#include "stm32f4xx_gpio.h"
#include "stm32f4xx_exti.h"
#include "stm32f4xx_flash.h"

#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include "Sys_Config.h"
#include "socket.h"
#include "w5500.h"
#include "drv_gpio.h"
#include "drv_delay.h"
#include "drv_ads1251.h"
#include "drv_checkcrc.h"

#include "app_UserTask.h"
#include "app_ForceOut.h"
#include "app_Communication.h"

extern uint8_t  USELED_Blink ;

#endif
