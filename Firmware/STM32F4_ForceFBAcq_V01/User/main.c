/**********************************************************************
** 创建工程    2024-04-13  
**********************************************************************/
#include "common.h"

uint8_t gRTOS_Start = 0;  //RTOS启动标识 

int main(void)
{
	SystemInit();	 
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
	delay_init(168);
	GPIO_OutInit();
	ADS1251_GPIOInit();
	TIM2_Config(9,83);
	xTaskCreate((TaskFunction_t )Start_Task,            
              (const char*    )"Start_Task",          
              (uint16_t       )START_STK_SIZE,        
              (void*          )NULL,
              (UBaseType_t    )START_TASK_PRIO,
              (TaskHandle_t*  )&StartTask_Handler);

  vTaskStartScheduler();
}

void Start_Task(void *pvParameters)
{
	taskENTER_CRITICAL();	
	
  gRTOS_Start = 1;
												
  xTaskCreate((TaskFunction_t )DataProcess_Task,           
							(const char*    )"DataProcess",        
							(uint16_t       )DATAPRO_STK_SIZE,     
							(void*          )NULL,              
							(UBaseType_t    )DATAPRO_TASK_PRIO,     
							(TaskHandle_t*  )&DataProcess_Handler); 	
							
	xTaskCreate((TaskFunction_t )Communication_Task,           
							(const char*    )"Communication",        
							(uint16_t       )COMMUN_STK_SIZE,     
							(void*          )NULL,              
							(UBaseType_t    )COMMUN_TASK_PRIO,     
							(TaskHandle_t*  )&CommunTask_Handler);  
							
	vTaskDelete(StartTask_Handler);
							
	taskEXIT_CRITICAL();
}


