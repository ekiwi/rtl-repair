module fsm_full
(
  clock,
  reset,
  req_0,
  req_1,
  req_2,
  req_3,
  gnt_0,
  gnt_1,
  gnt_2,
  gnt_3
);

  input clock;
  input reset;
  input req_0;
  input req_1;
  input req_2;
  input req_3;
  output gnt_0;
  output gnt_1;
  output gnt_2;
  output gnt_3;
  reg gnt_0;
  reg gnt_1;
  reg gnt_2;
  reg gnt_3;
  parameter [2:0] IDLE = 3'b000;
  parameter [2:0] GNT0 = 3'b001;
  parameter [2:0] GNT1 = 3'b010;
  parameter [2:0] GNT2 = 3'b011;
  parameter [2:0] GNT3 = 3'b100;
  reg [2:0] state;reg [2:0] next_state;

  always @(req_0 or req_1 or req_2 or req_3) begin
    case(state)
      IDLE: if(req_0 == 1'b1) begin
        next_state = GNT0;
      end else if(req_1 == 1'b1) begin
        next_state = GNT1;
      end else if(req_2 == 1'b1) begin
        next_state = GNT2;
      end else if(req_3 == 1'b1) begin
        next_state = GNT3;
      end else begin
        next_state = IDLE;
      end
      GNT0: if(req_0 == 1'b0) begin
        next_state = IDLE;
      end else begin
        next_state = GNT0;
      end
      GNT1: if(req_1 == 1'b0) begin
        next_state = IDLE;
      end else begin
        next_state = GNT1;
      end
      GNT2: if(req_2 == 1'b0) begin
        next_state = IDLE;
      end else begin
        next_state = GNT2;
      end
      GNT3: if(req_3 == 1'b0) begin
        next_state = IDLE;
      end else begin
        next_state = GNT3;
      end
    endcase
  end


  always @(posedge clock) begin : OUTPUT_LOGIC
    if(reset) begin
      gnt_0 <= #1 1'b0;
      gnt_1 <= #1 1'b0;
      gnt_2 <= #1 1'b0;
      gnt_3 <= #1 1'b0;
      state <= #1 IDLE;
    end else begin
      state <= #1 next_state;
      case(state)
        IDLE: begin
          gnt_0 <= #1 1'b0;
          gnt_1 <= #1 1'b0;
          gnt_2 <= #1 1'b0;
          gnt_3 <= #1 1'b0;
        end
        GNT0: begin
          gnt_0 <= #1 1'b1;
        end
        GNT1: begin
          gnt_1 <= #1 1'b1;
        end
        GNT2: begin
          gnt_2 <= #1 1'b1;
        end
        GNT3: begin
          gnt_3 <= #1 1'b1;
        end
        default: begin
          state <= #1 IDLE;
        end
      endcase
    end
  end


endmodule
