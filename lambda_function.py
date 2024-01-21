import json, logging, os, boto3, random, threading, openai
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from boto3.dynamodb.conditions import Key

BOT_TOKEN = os.environ['PROD_BOT_TOKEN']
API_KEY = os.environ['PROD_GPT_API_KEY']
SIGNING_SECRET = os.environ['PROD_SIGNING_SECRET']

app = App(
    token=BOT_TOKEN,
    signing_secret=SIGNING_SECRET,
    process_before_response=True
)

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
dbtable = dynamodb.Table('inha-pumpkin-coach')
handler = SlackRequestHandler(app)
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)
logger = logging.getLogger()

def random_name_generator():
    PK = 'namespace'
    SK = 'namespace'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 이름 데이터베이스 조회
    adjectives = response['Items'][0]['adjectives']
    adjective = adjectives[random.randrange(0,len(adjectives))]
    nouns = response['Items'][0]['nouns']
    noun = nouns[random.randrange(0,len(nouns))]
    name = adjective + ' ' + noun + ' ' + str(random.randrange(1,1001))
    return name

def respond_to_slack_within_3_seconds(ack):
    ack()


def chatgpt_response(message, say):
    
    # OpenAI API 키를 설정합니다
    openai.api_key = API_KEY
    
    # OpenAI를 사용하여 텍스트를 생성합니다
    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {"role": "system", "content": "You are a software engineer."},
            {"role": "user", "content" : message.content}
        ],
        #prompt=message['text'][5:],
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    
    say("답변: " + str(response['choices'][0]['message']['content']))

app.message("!GPT")(
    ack=respond_to_slack_within_3_seconds,
    lazy=[chatgpt_response]
)

@app.action("console_action_button") # 버튼 누를 시 콘솔 표시
def console_action_button(ack, say, client, body):
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    body["user_id"] = body["user"]["id"]
    print_console(ack,client,body)

@app.command("/주제-호박마차") # 콘솔 표시
def print_console(ack, client, body):
    ack()
    client.chat_postMessage(token=BOT_TOKEN, channel=body['user_id'],
    blocks= '''
            [
        		{
        			"type": "header",
        			"text": {
        				"type": "plain_text",
        				"text": ":jack_o_lantern: Pumpkin-Topic :jack_o_lantern:"
        			}
        		},
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "진행중인 주제의 목록을 보여줍니다."
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "목록"
        				},
        				"value": "list_action_button",
        				"action_id": "list_action_button"
        			}
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "주제 채팅에 입장합니다."
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "입장"
        				},
        				"value": "join_action_button",
        				"action_id": "join_action_button"
        			}
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "주제 채팅을 만들고 입장합니다."
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "만들기"
        				},
        				"value": "create_action_button",
        				"action_id": "create_action_button"
        			}
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "GPT에게 질문합니다."
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "GPT"
        				},
        				"value": "gpt_action_button",
        				"action_id": "gpt_action_button"
        			}
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "채팅방에서 나갑니다."
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "나가기"
        				},
        				"value": "exit_action_button",
        				"action_id": "exit_action_button"
        			}
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "주제채팅을 시작하기 위해 사용자를 등록합니다.\n:exclamation:서비스 이용을 위해 필수:exclamation:"
        			},
        			"accessory": {
        				"type": "button",
        				"text": {
        					"type": "plain_text",
        					"text": "등록"
        				},
        				"value": "regist_action_button",
        				"action_id": "regist_action_button"
        			}
        		}
	        ]
	        '''
    )

@app.action("list_action_button") # 목록 버튼
def list_action_button(ack, message, say, body, client):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    
    team_id = body["user"]["team_id"]
    PK = f'topic#{team_id}'
    SK = 'group#'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').begins_with(SK))
    if len(response['Items']) == 0:
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": "*채팅방이 존재하지 않습니다.*"
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "채팅 만들기"
            					},
            					"value": "create_action_button",
            					"action_id": "create_action_button"
            				}
            			]
            		}
        		]
    		}
        )
        return
    say(get_topics_format(response["Items"]))
    say(
            {
                "blocks" : [
                    {
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "채팅 입장"
            					},
            					"value": "join_action_button",
            					"action_id": "join_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				}
            			]
            		}
        		]
            }
        )
    return

def get_topics_format(items): # 개수 제한 로직 추가 필요 (pagination?)
    result = ''
    for item in items:
        result += f'- {item["SK"].split("#")[1]}\n'
    return {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": "*진행중인 주제*"
            			}
            		},
                    {
                        "type" : "context",
                        "elements" : [
                            {
                                "type" : "mrkdwn",
                                "text" : result
                            }
                        ]
                    }
        		]
    		}

@app.action("join_action_button") # 입장 버튼 (채팅방 이름 입력)
def join_action_button(ack, say, body, client):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    if body['actions'][0]['value'] != 'join_action_button_with_no_delete':
        client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    say(
        {
          "type": "modal",
          "blocks": [
            {
              "type": "input",
              "block_id": "input_block",
              "element": {
                "type": "plain_text_input",
                "action_id": "text_input_action"
              },
              "label": {
                "type": "plain_text",
                "text": "참가를 원하는 채팅방 이름을 입력해주세요."
              }
            },
            {
              "type": "actions",
              "block_id": "submit_button_block",
              "elements": [
                {
                  "type": "button",
                  "text": {
                    "type": "plain_text",
                    "text": "입장"
                  },
                  "action_id": "request_join_action"
                },
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "콘솔 열기"
					},
					"value": "console_action_button",
					"action_id": "console_action_button"
				}
              ]
            }
          ]
        }
    )

@app.action("request_join_action") # 입장 버튼
def request_join_action(ack, body, say, client):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    topic = body["state"]["values"]["input_block"]["text_input_action"]["value"]
    
    team = body["user"]["team_id"]
    user = body["user"]["id"]
    PK = f'topic#{team}'
    
    # 사용자가 현재 주제채팅에 존재한다면 이동못하도록 제지
    SK = f'user#{user}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK))
    if response['Items'][0]['topic'] != '':
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": f'*현재 {response["Items"][0]["topic"]} 주제채팅방에 있어 {topic} 주제채팅방으로 이동할 수 없습니다.\n주제채팅방에서 나간 후 새로운 주제 채팅방으로 이동하세요.*'
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "나가기"
            					},
            					"value": "exit_action_button",
            					"action_id": "exit_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				}
            			]
            		}
        		]
    		}
        )
        return
    SK = f'group#{topic}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 주제채팅 그룹 데이터 조회
    
    if response['Count'] == 0:
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": f'*{topic} 채팅방은 존재하지 않습니다.*'
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "채팅 만들기"
            					},
            					"value": "create_action_button",
            					"action_id": "create_action_button"
            				}
            			]
            		}
        		]
    		}
        )
        return
    
    # 새로운 그룹에 사용자 주제채팅 채널 등록
    channels = response["Items"][0]['channels']
    channels.append(channel)
    SK = f'group#{topic}'
    response = dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'channels': {'Value': channels, 'Action': 'PUT'}}, ReturnValues='ALL_NEW')
    messages = response['Attributes']['messages']
    
    # 익명 이름 생성, 사용자 nickName, topic 저장 구현
    new_nickName = random_name_generator()
    SK = f'user#{user}'
    response = dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'nickName': {'Value': new_nickName, 'Action': 'PUT'}, 'topic': {'Value': topic, 'Action': 'PUT'}}, ReturnValues='ALL_OLD')
    
    response = client.conversations_setTopic(token=BOT_TOKEN,channel=channel,topic=f'{topic} 주제채팅방에 {new_nickName} 으로 참여중')
    client.chat_delete(token=BOT_TOKEN, channel=channel,ts=response['channel']['latest']['ts'])
    
    say(
        {
            "blocks": [
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": f'*{new_nickName}님, {topic} 주제채팅방에 접속하였습니다.*'
        			}
        		},
    		    {
        			"type": "context",
        			"elements": [
        				{
        					"type": "mrkdwn",
        					"text": message_loader(messages)
        				}
        			]
        		}
    		]
		}
    )
    publish_message(channels=channels, text=f'{new_nickName} 님이 채팅방에 참가 하였습니다.', say=say, nickName=new_nickName)
    return
    
def message_loader(messages): # 채팅방의 이전 메세지를 불러옴
    result = ''
    for key, message in sorted(messages.items()):
        result += message + '\n'
    return result

@app.action("create_action_button") # 만들기 버튼 (채팅방 이름 입력)
def create_action_button(ack, say, body, client):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    say(
        {
          "type": "modal",
          "blocks": [
            {
              "type": "input",
              "block_id": "input_block",
              "element": {
                "type": "plain_text_input",
                "action_id": "text_input_action"
              },
              "label": {
                "type": "plain_text",
                "text": "생성할 채팅방 이름을 입력해주세요."
              }
            },
            {
              "type": "actions",
              "block_id": "submit_button_block",
              "elements": [
                {
                  "type": "button",
                  "text": {
                    "type": "plain_text",
                    "text": "생성"
                  },
                  "action_id": "create_topic_action"
                },
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "콘솔 열기"
					},
					"value": "console_action_button",
					"action_id": "console_action_button"
				}
              ]
            }
          ]
        }
    )

@app.action("create_topic_action") # 만들기 버튼
def create_topic_action(ack, message, say, client, body):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    
    team = body["user"]["team_id"]
    user = body["user"]["id"]
    channel = body["channel"]["id"]
    
    topic = body["state"]["values"]["input_block"]["text_input_action"]["value"]
    PK = f'topic#{team}'
    
    # 사용자가 현재 주제채팅에 존재한다면 이동못하도록 제지
    SK = f'user#{user}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK))
    if response['Items'][0]['topic'] != '':
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": f'*현재 {response["Items"][0]["topic"]} 주제채팅방에 있어 {topic} 주제채팅방으로 이동할 수 없습니다.\n주제채팅방에서 나간 후 새로운 주제 채팅방으로 이동하세요.*'
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "나가기"
            					},
            					"value": "exit_action_button",
            					"action_id": "exit_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				}
            			]
            		}
        		]
    		}
        )
        return
    
    SK = f'group#{topic}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 주제채팅의 그룹 데이터 조회
    
    # 주제채팅의 사용자 데이터 수정
    SK = f'user#{user}'
    new_nickName = random_name_generator()
    dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'nickName': {'Value': new_nickName, 'Action': 'PUT'}, 'topic': {'Value': topic, 'Action': 'PUT'}})
    
    response_setTopic = client.conversations_setTopic(token=BOT_TOKEN,channel=channel,topic=f'{topic} 주제채팅방에 {new_nickName} 으로 참여중')
    client.chat_delete(token=BOT_TOKEN, channel=channel,ts=response_setTopic['channel']['latest']['ts'])
    
    if len(response['Items']) != 0: # 해당 주제 채팅이 이미 존재하는 경우
        channels = response['Items'][0]['channels']
        channels.append(channel)
        SK = f'group#{topic}'
        dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'channels': {'Value': channels, 'Action': 'PUT'}})
        
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": f'*{new_nickName}님, 이미 존재하는 {topic} 주제채팅방에 접속하였습니다.*'
            			}
            		},
        		    {
            			"type": "context",
            			"elements": [
            				{
            					"type": "mrkdwn",
            					"text": message_loader(response['Items'][0]['messages'])
            				}
            			]
            		}
        		]
    		}
        )
        publish_message(channels=channels, text=f'{new_nickName} 님이 채팅방에 참가 하였습니다.', say=say, nickName=new_nickName)
        return
    
    # 해당 주제 채팅이 존재하지 않는 경우
    
    # 주제채팅의 그룹 데이터 생성
    channels = list()
    channels.append(channel)
    messages = dict()
    SK = f'group#{topic}'
    dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'channels': {'Value': channels, 'Action': 'PUT'}, 'messages' : {'Value': messages, 'Action': 'PUT'}})
    say(
        {
            "blocks": [
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": f'*{new_nickName}님, 새롭게 생성된 {topic} 주제채팅방에 접속하였습니다.*'
        			}
        		}
    		]
		}
    )
    publish_message(channels=channels, text=f'{new_nickName} 님이 채팅방에 참가 하였습니다.', say=say, nickName=new_nickName)
    return

@app.action("gpt_action_button")
def gpt_action_button(ack, say, client, body):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    say(
        {
    	"blocks": [
    		{
    			"type": "divider"
    		},
    		{
    			"type": "input",
    			"element": {
    				"type": "plain_text_input",
    				"action_id": "plain_text_input-action"
    			},
    			"label": {
    				"type": "plain_text",
    				"text": "GPT에게 물어볼것을 입력해주세요."
    			}
    		},
    		{
    			"type": "actions",
    			"elements": [
    				{
    					"type": "button",
    					"text": {
    						"type": "plain_text",
    						"text": "입력"
    					},
    					"value": "gpt_action",
    					"action_id": "gpt_action"
    				},
    				{
    					"type": "button",
    					"text": {
    						"type": "plain_text",
    						"text": "콘솔 열기"
    					},
    					"value": "console_action_button",
    					"action_id": "console_action_button"
    				}
    			]
    		}
    	]
    }
    )

@app.action("exit_action_button") # 나가기 버튼
def exit_action_button(ack, say, client, body):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    
    team = body["user"]["team_id"]
    user = body["user"]["id"]
    channel = body["channel"]["id"]
    PK = f'topic#{team}'
    SK = f'user#{user}'
    
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 주제채팅 사용자 데이터 조회
    topic = response['Items'][0]['topic'] # 주제채팅 사용자가 속한 주제채팅 조회
    nickName = response['Items'][0]['nickName']
    if topic == '': # 소속한 주제채팅이 존재하지 않는 경우
        say(
            {
        	"blocks": [
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": "*현재 채팅방에 존재하지 않습니다.*"
        			}
        		},
        		{
        			"type": "actions",
        			"elements": [
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "콘솔 열기"
        					},
        					"value": "console_action_button",
        					"action_id": "console_action_button"
        				},
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "채팅 목록"
        					},
        					"value": "list_action_button",
        					"action_id": "list_action_button"
        				}
        			]
        		}
        	]
        }
        )
        return
    
    # 데이터베이스에서 사용자 nickName 제거, topic 제거
    dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'topic': {'Value': '', 'Action':'PUT'}, 'nickName': {'Value': '', 'Action': 'PUT'}}) # 주제채팅 사용자 데이터 수정
    SK = f'group#{topic}' # 주제채팅 그룹 sort key
    
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 주제채팅 그룹 데이터 조회
    channels = response['Items'][0]['channels'] # 주제채팅 그룹 내 속한 사용자들의 채널 id 조회
    publish_message(channels=channels, text=f'{nickName} 님이 채팅방에 나갔습니다.', say=say, nickName=nickName)
    
    # 주제채팅방에서 channel_id 제거
    if len(response['Items'][0]['channels']) <= 1: # 주제 채팅방에 남아있는 사람이 없는 경우
        response = dbtable.delete_item(Key={'PK':PK,'SK':SK})
    else: # 주제 채팅방에 남아 있는 사람이 있는 경우
        channels.remove(channel)
        response = dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'channels': {'Value': channels, 'Action': 'PUT'}})
    
    response = client.conversations_setTopic(token=BOT_TOKEN,channel=channel,topic='속한 채팅방 없음. 대화를 시작해보세요!')
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=response['channel']['latest']['ts'])
    say(
        {
            "blocks": [
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": f"*{topic} 주제채팅방을 나갑니다.*"
        			}
        		},
        		{
        			"type": "actions",
        			"elements": [
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "콘솔 열기"
        					},
        					"value": "console_action_button",
        					"action_id": "console_action_button"
        				},
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "채팅 목록"
        					},
        					"value": "list_action_button",
        					"action_id": "list_action_button"
        				}
        			]
        		}
    		]
		}
    )
    return

@app.action("regist_action_button") # 등록 버튼
def regist_action_button(ack, say, client, body):
    ack()
    channel = body["channel"]["id"]
    join_action_button_modal_ts = body["message"]["ts"]
    client.chat_delete(token=BOT_TOKEN, channel=channel, ts=join_action_button_modal_ts)
    
    team = body["user"]["team_id"]
    user = body["user"]["id"]
    PK = f'topic#{team}'
    SK = f'user#{user}'
    
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK)) # 주제채팅 사용자 데이터 조회
    if response['ScannedCount'] != 0 :
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": '*이미 사용자 정보가 등록되어 있습니다.*'
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				}
            			]
            		}
        		]
            }
        )
        return
    
    dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'channel': {'Value':user, 'Action':'PUT'},'topic': {'Value': '', 'Action':'PUT'}, 'nickName': {'Value': '', 'Action': 'PUT'}}) # 주제채팅 사용자 데이터 수정
    say(
        {
            "blocks": [
        		{
        			"type": "divider"
        		},
        		{
        			"type": "section",
        			"text": {
        				"type": "mrkdwn",
        				"text": '*주제채팅방에 사용자 정보가 등록되었습니다.*'
        			}
        		},
        		{
        			"type": "actions",
        			"elements": [
        				{
        					"type": "button",
        					"text": {
        						"type": "plain_text",
        						"text": "콘솔 열기"
        					},
        					"value": "console_action_button",
        					"action_id": "console_action_button"
        				}
        			]
        		}
    		]
		}
    )
    return

@app.message() # 채팅
def message_receive(ack, message, say):
    ack()
    print('message : ' + str(message))
    text = message['text']
    team = message['team']
    user = message['user']
    channel = message['channel']
    ts = message['ts']
    
    PK = f'topic#{team}'
    SK = f'user#{user}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK))
    nickName = response['Items'][0]['nickName']
    topic = response['Items'][0]['topic']
    
    if topic == '':
        say(
            {
                "blocks": [
            		{
            			"type": "divider"
            		},
            		{
            			"type": "section",
            			"text": {
            				"type": "mrkdwn",
            				"text": '*현재 채팅방에 존재하지 않습니다.*'
            			}
            		},
            		{
            			"type": "actions",
            			"elements": [
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "콘솔 열기"
            					},
            					"value": "console_action_button",
            					"action_id": "console_action_button"
            				},
            				{
            					"type": "button",
            					"text": {
            						"type": "plain_text",
            						"text": "채팅 목록"
            					},
            					"value": "list_action_button",
            					"action_id": "list_action_button"
            				}
            			]
            		}
        		]
    		}
        )
        return
    
    SK = f'group#{topic}'
    response = dbtable.query(Select='ALL_ATTRIBUTES',KeyConditionExpression=Key('PK').eq(PK)&Key('SK').eq(SK))
    channels = response['Items'][0]['channels']
    messages = response['Items'][0]['messages']
    
    # channels.remove(channel)
    
    pub_text = f'*{nickName}* {text}'
    messages[ts] = pub_text
    dbtable.update_item(Key={'PK':PK,'SK':SK}, AttributeUpdates={'messages' : {'Value': messages, 'Action': 'PUT'}})
    
    publish_message(channels, nickName, text, say)
    return
    
def publish_message(channels, nickName, text, say):
    # threads = []
    for channel in channels:
        send_message(channel, nickName, text, say)
        # t = threading.Thread(target=send_message, args=(channel, nickName, text, say,))
        # threads.append(t)
    
    # for t in threads:
    #     t.start()
    
    # for t in threads:
    #     t.join()
        
    return

def send_message(channel, nickName, text, say):
    say(text=text ,channel=channel, username=nickName)
    return

def lambda_handler(event, context):
	return handler.handle(event, context)
