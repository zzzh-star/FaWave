#ifndef _USERTASK_H_
#define _USERTASK_H_

#include "common.h"
  
#define START_TASK_PRIO		  5         
#define START_STK_SIZE 		  1024      

#define DATAPRO_TASK_PRIO		3       //任务优先级       
#define DATAPRO_STK_SIZE 		1024    //任务堆栈

#define COMMUN_TASK_PRIO		4          
#define COMMUN_STK_SIZE 		1152    


extern TaskHandle_t   StartTask_Handler;
extern TaskHandle_t   CommunTask_Handler; 
extern TaskHandle_t   DataProcess_Handler;


void  Start_Task (void *pvParameters);
void  DataProcess_Task(void *pvParameters);
void  Communication_Task(void *pvParameters);
	
#endif 
