#include "app_UserTask.h"

#define USE_UNTDELAY         0     //RTOS是否使用绝对延时 0不使用 

TaskHandle_t  StartTask_Handler;
TaskHandle_t  CommunTask_Handler;  
TaskHandle_t  DataProcess_Handler; 
ForceResult_t fRes;

void DataProcess_Task(void *pvParameters)
{
#if USE_UNTDELAY	
	TickType_t        dPreviousWakeTime;
	const TickType_t  dTimeIncrement = pdMS_TO_TICKS(1);
	dPreviousWakeTime = xTaskGetTickCount(); 
#endif
	vTaskDelay(500);
  ForceSensor_Init(volData);	
	while(1)
	{
    ForceSensor_Update(volData,g_tick_ms,&fRes);
		
#if USE_UNTDELAY
		vTaskDelayUntil(&dPreviousWakeTime,dTimeIncrement);
#else	
    vTaskDelay(10);		
#endif			
	}
}


void Communication_Task(void *pvParameters)
{
#if USE_UNTDELAY	
	TickType_t          cPreviousWakeTime;
	const TickType_t    cTimeIncrement = pdMS_TO_TICKS(12);
	cPreviousWakeTime = xTaskGetTickCount(); 
#endif	
  W5500_Init();
	vTaskDelay(20);
	NetWork_Register();
	
	while(1)
	{
		OnNetProc();         
		TimeOut_Check();     
	  IPC_OfflineDisPose();    
#if USE_UNTDELAY	
		vTaskDelayUntil(&cPreviousWakeTime,cTimeIncrement); //任务挂起 12 ms	 
#else
		vTaskDelay(12);
#endif				
	}
}


